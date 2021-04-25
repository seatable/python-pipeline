import json
import logging
import os
import random
import requests
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from flask import Flask, request, make_response

import settings


if not settings.DEBUG:
    logging.basicConfig(
        filename='/var/log/function.log',
        filemode='a',
        format="%(asctime)s-%(name)s-%(levelname)s-%(message)s",
        level=logging.WARNING
    )

app = Flask(__name__)
executor = ThreadPoolExecutor(settings.THREAD_COUNT)

DEFAULT_SUB_PROCESS_TIMEOUT = settings.SUB_PROCESS_TIMEOUT


def send_to_scheduler(success, return_code, output, spend_time, request_data):
    """
    This function is used to send result of script to scheduler

    success: whether script running successfully
    return_code: return-code of subprocess
    output: output of subprocess or error message
    spend_time: time subprocess took
    request_data: data from request
    """
    if not settings.SCHEDULER_URL:
        logging.error('SCHEDULER_URL not set!')
        return

    url = settings.SCHEDULER_URL.strip('/') + '/script-result/'

    result_data = {
        'success': success,
        'return_code': return_code,
        'output': output,
        'spend_time': spend_time
    }

    result_data.update({
        'script_id': request_data.get('script_id'),
        'task_log_id': request_data.get('task_log_id')
    })

    try:
        response = requests.post(url, json=result_data, timeout=30)
    except Exception as e:
        logging.error('send to scheduler: %s, error: %s, result_data: %s', url, e, result_data)
        return

    if response.status_code != 200:
        logging.error('Fail to send to scheduler, response: %s, result_data: %s', response, result_data)


def run_python(data):
    script_url = data.get('script_url')
    if not script_url:
        send_to_scheduler(False, None, 'Script URL is missing', None, data)
        return

    # env must be map
    env = data.get('env')
    if env and not isinstance(env, dict):
        env = {}
    env['is_cloud'] = "1"

    # context_data must be map
    context_data = data.get('context_data')
    if context_data and not isinstance(context_data, dict):
        context_data = None
    context_data = json.dumps(context_data) if context_data else None

    try:
        resp = requests.get(script_url)
        if resp.status_code < 200 or resp.status_code >= 300:
            logging.error('Fail to get script: %s, response: %s', script_url, resp)
            send_to_scheduler(False, None, 'Fail to get script', None, data)
            return
    except Exception as e:
        logging.error('Fail to get script %s, error: %s', script_url, e)
        send_to_scheduler(False, None, 'Fail to get script', None, data)
        return

    dir_id = uuid4().hex
    container_name = 'python-runner' + dir_id
    file_name = 'index.py'
    os.makedirs(dir_id)
    # save script
    with open(os.path.join(dir_id, file_name), 'wb') as f:
        f.write(resp.content)
    # save env
    env_file = os.path.join(dir_id, 'env.list')
    with open(env_file, 'w') as f:
        if env:
            envs = '\n'.join(['%s=%s' % (key, value) for key, value in env.items()])
            f.write(envs)
    # save arguments as file to stdin
    with open(os.path.join(dir_id, 'input'), 'w') as f:
        if context_data:
            f.write(context_data)

    return_code, output = None, None  # init output

    # generate command
    scripts_path = os.path.join(os.getcwd(), dir_id)
    # mount volumes and set env
    command = ['docker', 'run', '--name', container_name,
               '--env-file', env_file,
               '-v', '{}:/scripts'.format(scripts_path)]
    # limit memory and cpus
    if settings.CONTAINER_MEMORY:
        command.append('--memory={}'.format(settings.CONTAINER_MEMORY))
    if settings.CONTAINER_CPUS:
        command.append('--cpus={}'.format(settings.CONTAINER_CPUS))
    command.append(settings.IMAGE)
    command.append('run')  # override command

    start_at = time.time()
    try:
        result = subprocess.run(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                timeout=DEFAULT_SUB_PROCESS_TIMEOUT)
    except subprocess.TimeoutExpired as e:
        try:  # stop container
            subprocess.run(['docker', 'stop', container_name], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except Exception as e:
            logging.warning('stop script: %s container: %s, error: %s', script_url, container_name, e)
        send_to_scheduler(False, -1, 'Script running for too long time!', DEFAULT_SUB_PROCESS_TIMEOUT, data)
        return
    except Exception as e:
        logging.exception(e)
        logging.error('Fail to run file %s error: %s', script_url, e)
        send_to_scheduler(False, None, None, None, data)
        return
    else:
        output_file_path = os.path.join(dir_id, 'output')
        if os.path.isfile(output_file_path):
            with open(output_file_path, 'r') as f:
                output = f.read()
        return_code = result.returncode
        if return_code == 137:  # OOM
            output += 'out-of-memory(OOM) error!\n'
        output += result.stdout.decode()
    finally:
        spend_time = time.time() - start_at
        try:
            shutil.rmtree(dir_id)
        except Exception as e:
            logging.warning('Fail to remove script files error: %s', e)
        try:
            subprocess.run(['docker', 'container', 'rm', container_name], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except Exception as e:
            logging.warning('Fail to remove container error: %s', e)

    send_to_scheduler(return_code == 0, return_code, output, spend_time, data)


@app.route("/", defaults={"path": ""}, methods=["POST", "GET"])
@app.route('/function/run-python', defaults={"path": ""}, methods=["POST", "GET"])
def main_route(path):
    try:
        data = request.get_json()
    except:
        return make_response('Bad Request.', 400)
    try:
        executor.submit(run_python, data)
    except Exception as e:
        logging.error(e)
        return make_response('Internal Server Error.', 500)
    return make_response('Received', 200)


@app.route("/_/health", methods=["POST", "GET"])
def health_check():
    return 'Everything is ok.'


if __name__ == "__main__":
    app.run(port=8088, debug=True)
