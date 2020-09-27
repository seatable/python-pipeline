import json
import logging
import os
import requests
import subprocess
from uuid import uuid4

from flask import make_response


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
    if env and isinstance(env, dict):
        os.environ.update(env)

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

    output = None  # init output

    try:
        result = subprocess.run(['python', file_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        logging.error('run file %s error: %s', script_url, e)
        return make_response(('Run error', 500))
    else:
        output = result.stdout.decode()
    finally:
        try:
            os.remove(file_name)
        except:
            pass

    return make_response((json.dumps({
        'output': output
    }), 200))
