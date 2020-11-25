from gevent import monkey
monkey.patch_all()

import json
import logging
from flask import Flask, request, make_response
from gevent.pywsgi import WSGIServer

from faas_scheduler import DBSession
from faas_scheduler.utils import check_auth_token, get_asset_id, get_script_url, \
    get_temp_api_token, call_faas_func, add_task, get_task, update_task, \
    delete_task, list_task_logs, get_task_log

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.route('/run-script/', methods=['POST'])
def scripts_api():
    if not check_auth_token(request):
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
    context_data = data.get('context_data')
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

    result = call_faas_func(script_url, temp_api_token, context_data)
    if not result:
        return make_response(('Internal server error', 500))

    return make_response((result, 200))


@app.route('/tasks/', methods=['POST'])
def tasks_api():
    if not check_auth_token(request):
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
    context_data = data.get('context_data')
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
            db_session, repo_id, dtable_uuid, script_name, context_data, trigger, is_active)
        return make_response(({'task': task.to_dict()}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()


@app.route('/tasks/<dtable_uuid>/<script_name>/', methods=['GET', 'PUT', 'DELETE'])
def task_api(dtable_uuid, script_name):
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    db_session = DBSession()
    try:
        task = get_task(db_session, dtable_uuid, script_name)
        if not task:
            return make_response(({'task': None}, 200))

        if request.method == 'GET':
            return make_response(({'task': task.to_dict()}, 200))

        elif request.method == 'PUT':
            try:
                data = json.loads(request.data)
                if not isinstance(data, dict):
                    return make_response(('Bad request', 400))
            except Exception as e:
                return make_response(('Bad request', 400))

            context_data = data.get('context_data')
            trigger = data.get('trigger', None)
            is_active = data.get('is_active', None)
            task = update_task(db_session, task, context_data, trigger, is_active)
            return make_response(({'task': task.to_dict()}, 200))

        elif request.method == 'DELETE':
            delete_task(db_session, task)
            return make_response(({'success': True}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()

@app.route('/tasks/<dtable_uuid>/<script_name>/logs/', methods=['GET'])
def task_logs_api(dtable_uuid, script_name):
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    try:
        current_page = int(request.args.get('page', '1'))
        per_page = int(request.args.get('per_page', '20'))
    except ValueError:
        current_page = 1
        per_page = 20
    start = per_page * (current_page - 1)
    end = start + per_page

    db_session = DBSession()
    try:
        task = get_task(db_session, dtable_uuid, script_name)
        if not task:
            return make_response(({
                'task_logs': [],
                'count': 0,
            }, 200))

        task_logs = list_task_logs(db_session, task.id)
        count = task_logs.count()
        task_logs = task_logs[start: end]
        task_log_list = [task_log.to_dict() for task_log in task_logs]
        return make_response(({
            'task_logs': task_log_list,
            'count': count,
        }, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()

@app.route('/tasks/<dtable_uuid>/<script_name>/logs/<log_id>/', methods=['GET'])
def task_log_api(dtable_uuid, script_name, log_id):
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    db_session = DBSession()
    try:
        task = get_task(db_session, dtable_uuid, script_name)
        if not task:
            return make_response(({'task_log': None}, 200))
        task_log = get_task_log(db_session, log_id)
        if not task_log or task_log.task_id != task.id:
            return make_response(({'task_log': None}, 200))

        task_log_info= task_log.to_dict()
        task_log_info['output'] = task_log.output
        return make_response(({'task_log': task_log_info}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()

if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5055), app)
    http_server.serve_forever()
