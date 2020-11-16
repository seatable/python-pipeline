import json
import logging
import os
import requests
import subprocess
import time
from uuid import uuid4

from flask import make_response

DEFAULT_SUB_PROCESS_TIMEOUT = 9


def get_sub_proc_timeout():
    sub_proc_timeout = os.environ.get('sub_proc_timeout').strip()
    if not sub_proc_timeout:
        return DEFAULT_SUB_PROCESS_TIMEOUT
    threed_end = sub_proc_timeout[-3:]
    if threed_end.lower() == 'min':
        try:
            return int(sub_proc_timeout[:-3]) * 60
        except:
            return DEFAULT_SUB_PROCESS_TIMEOUT
    if threed_end.lower() == 'sec':
        try:
            return int(sub_proc_timeout[:-3])
        except:
            return DEFAULT_SUB_PROCESS_TIMEOUT

    one_end = sub_proc_timeout[-1]
    if one_end in ('m', 'M'):
        try:
            return int(sub_proc_timeout[:-1]) * 60
        except:
            return DEFAULT_SUB_PROCESS_TIMEOUT
    if one_end in ('s', 'S'):
        try:
            return int(sub_proc_timeout[:-1])
        except:
            return DEFAULT_SUB_PROCESS_TIMEOUT

    return DEFAULT_SUB_PROCESS_TIMEOUT


def handle(req):
    """handle a request to the function
    Args:
        req (str): request body
    """
    try:
        data = json.loads(req)
        if not isinstance(data, dict):
            return make_response(('Bad request', 400))
    except Exception as e:
        return make_response(('Bad request', 400))

    script_url = data.get('script_url')
    if not script_url:
        return make_response(('script_url invalid', 400))

    env = data.get('env')
    # env must be map
    if env and not isinstance(env, dict):
        env = {}
    env['is_cloud'] = "1"
    env.update(os.environ)

    # context_data must be map
    context_data = data.get('context_data')
    if context_data and not isinstance(context_data, dict):
        context_data = None
    context_data = json.dumps(context_data).encode() if context_data else None

    try:
        resp = requests.get(script_url)
        if resp.status_code < 200 or resp.status_code >= 300:
            logging.error('request %s status code: %s', script_url, resp.status_code)
            return make_response(('URL error', 400))
    except Exception as e:
        logging.error('request %s error: %s', script_url, e)
        return make_response(('URL error', 400))

    file_name = uuid4().hex + '.py'
    with open(file_name, 'wb') as f:
        f.write(resp.content)

    return_code, output = None, None  # init output

    start_at = time.time()
    try:
        result = subprocess.run(['python', file_name],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                input=context_data,
                                env=env,
                                timeout=get_sub_proc_timeout())
    except subprocess.TimeoutExpired as e:
        return make_response(('Script running for too long time!', 400))
    except Exception as e:
        logging.error('run file %s error: %s', script_url, e)
        return make_response(('Run error', 500))
    else:
        return_code = result.returncode
        output = result.stdout.decode()
    finally:
        spend_time = time.time() - start_at
        try:
            os.remove(file_name)
        except:
            pass

    return make_response((json.dumps({
        'output': output,
        'return_code': return_code,
        'spend_time': spend_time
    }), 200))
