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

    try:
        resp = requests.get(req)
        if resp.status_code < 200 or resp.status_code >= 300:
            logging.error('request %s status code: %s', req, resp.status_code)
            return make_response(('URL error', 400))
    except Exception as e:
        logging.error('request %s error: %s', req, e)
        return make_response(('URL error', 400))

    file_name = uuid4().hex + '.py'
    with open(file_name, 'wb') as f:
        f.write(resp.content)

    try:
        subprocess.check_call(['python', file_name])
    except Exception as e:
        logging.error('run file %s error: %s', req, e)
        return make_response(('Run error', 500))
    finally:
        try:
            os.remove(file_name)
        except:
            pass
    return make_response(('', 200))
