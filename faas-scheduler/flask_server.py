from gevent import monkey
monkey.patch_all()

import json
import logging
from flask import Flask, request, make_response
from gevent.pywsgi import WSGIServer

from faas_scheduler import DBSession
from faas_scheduler.utils import check_auth_key, get_asset_id, get_script_url, \
    get_temp_api_token, call_faas_func, add_task, get_task, update_task, delete_task

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/script/run/', methods=['POST'])
def run_script():
    if not check_auth_key(request):
        return make_response(('Forbidden', 403))

    try:
        data = json.loads(request.data)
        if not isinstance(data, dict):
            return make_response(('Bad request', 400))
    except Exception as e:
        return make_response(('Bad request', 400))

    repo_id = data.get('repo_id')
    dtable_uuid = data.get('dtable_uuid')
    script_name = data.get('script_name')
    if not repo_id \
            or not dtable_uuid \
            or not script_name:
        return make_response(('Parameters invalid', 400))

    # main
    asset_id = get_asset_id(repo_id, dtable_uuid, script_name)
    if not asset_id:
        return make_response(('Not found', 404))

    script_url = get_script_url(repo_id, asset_id, script_name)
    if not script_url:
        return make_response(('Not found', 404))

    temp_api_token = get_temp_api_token(dtable_uuid, script_name)

    result = call_faas_func(script_url, temp_api_token)
    if not result:
        return make_response(('Internal server error', 500))

    return make_response((result, 200))


@app.route('/tasks/', methods=['POST'])
def tasks():
    if not check_auth_key(request):
        return make_response(('Forbidden', 403))

    try:
        data = json.loads(request.data)
        if not isinstance(data, dict):
            return make_response(('Bad request', 400))
    except Exception as e:
        return make_response(('Bad request', 400))

    repo_id = data.get('repo_id')
    dtable_uuid = data.get('dtable_uuid')
    script_name = data.get('script_name')
    trigger = data.get('trigger')
    is_active = data.get('is_active', True)
    if not repo_id \
            or not dtable_uuid \
            or not script_name \
            or not trigger:
        return make_response(('Parameters invalid', 400))

    # main
    db_session = DBSession()
    try:
        task_in_db = get_task(db_session, dtable_uuid, script_name)
        if task_in_db:
            return make_response(('task exists', 400))

        task = add_task(
            db_session, repo_id, dtable_uuid, script_name, trigger, is_active)
    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))

    return make_response(({'task': task.to_dict()}, 200))


@app.route('/tasks/<dtable_uuid>/<script_name>/', methods=['GET', 'PUT', 'DELETE'])
def task(dtable_uuid, script_name):
    if not check_auth_key(request):
        return make_response(('Forbidden', 403))

    try:
        db_session = DBSession()
        task = get_task(db_session, dtable_uuid, script_name)
        if not task:
            make_response(('Not found', 404))

        if request.method == 'GET':
            return make_response(({'task': task.to_dict()}, 200))

        elif request.method == 'PUT':
            try:
                data = json.loads(request.data)
                if not isinstance(data, dict):
                    return make_response(('Bad request', 400))
            except Exception as e:
                return make_response(('Bad request', 400))

            trigger = data.get('trigger', None)
            is_active = data.get('is_active', None)
            task = update_task(db_session, task, trigger, is_active)
            return make_response(({'task': task.to_dict()}, 200))

        elif request.method == 'DELETE':
            delete_task(db_session, task)
            return make_response(({'success': True}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5055), app)
    http_server.serve_forever()
