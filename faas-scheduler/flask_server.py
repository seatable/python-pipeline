from gevent import monkey
monkey.patch_all()

import json
import logging
from datetime import datetime
from flask import Flask, request, make_response
from gevent.pywsgi import WSGIServer
from concurrent.futures import ThreadPoolExecutor

from faas_scheduler import DBSession
import faas_scheduler.settings as settings
from faas_scheduler.utils import check_auth_token, get_asset_id, get_script_url, \
    get_temp_api_token, add_task, get_task, update_task, delete_task, list_task_logs, \
    get_task_log, run_script, get_script, add_script, delete_task_logs, \
    update_statistics, get_run_script_statistics_by_month

app = Flask(__name__)
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=settings.SCRIPT_WORKERS)


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
    owner = data.get('owner')  # todo: owner???
    if not repo_id \
            or not dtable_uuid \
            or not script_name \
            or not owner:
        return make_response(('Parameters invalid', 400))

    # check
    asset_id = get_asset_id(repo_id, dtable_uuid, script_name)
    if not asset_id:
        return make_response(('Not found', 404))

    script_url = get_script_url(repo_id, asset_id, script_name)
    if not script_url:
        return make_response(('Not found', 404))

    temp_api_token = get_temp_api_token(dtable_uuid, script_name)

    # main
    db_session = DBSession()
    try:
        script = add_script(db_session, repo_id, dtable_uuid, script_name, context_data)
        executor.submit(run_script, script.id, script_url, temp_api_token, context_data)

        return make_response(({'script_id': script.id}, 200))
    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()


@app.route('/run-script/<script_id>/', methods=['GET'])
def script_api(script_id):
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    try:
        script_id = int(script_id)
    except Exception as e:
        return make_response(('Bad request', 400))
    dtable_uuid = request.args.get('dtable_uuid')
    script_name = request.args.get('script_name')
    if not dtable_uuid or not script_name:
        return make_response(('Parameters invalid', 400))

    # main
    db_session = DBSession()
    try:
        script = get_script(db_session, script_id)
        if not script:
            return make_response(('Not found', 404))
        if dtable_uuid != script.dtable_uuid \
                or script_name != script.script_name:
            return make_response(('Bad request', 400))

        return make_response(({'script': script.to_dict()}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()


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
    owner = data.get('owner')
    if not repo_id \
            or not dtable_uuid \
            or not script_name \
            or not trigger \
            or not owner:
        return make_response(('Parameters invalid', 400))

    # main
    db_session = DBSession()
    try:
        task_in_db = get_task(db_session, dtable_uuid, script_name)
        if task_in_db:
            return make_response(('task exists', 400))

        task = add_task(
            db_session, repo_id, dtable_uuid, owner, script_name, context_data, trigger, is_active)
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
            task_id = task.id
            delete_task(db_session, task)
            delete_task_logs(db_session, task_id)
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


@app.route('/admin/statistics/run-scripts/', methods=['GET'])
def user_run_python_statistics():
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    raw_month = request.args.get('month')
    if raw_month:
        try:
            month = datetime.strptime(raw_month, '%Y-%m')
        except:
            return make_response(('month invalid.', 400))
    else:
        month = None

    order_by = request.args.get('order_by')
    if order_by:
        if order_by.strip('-') not in ('total_run_time', 'total_run_count'):
            return make_response(('order_by invalid.', 400))
        if '-' in order_by:
            order_by = order_by.strip('-') + ' DESC'

    try:
        is_user = int(request.args.get('is_user', 1))
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
    except:
        is_user = 1
        page, per_page = 1, 25

    start, limit = (page - 1) * per_page, per_page

    db_session = DBSession()
    try:
        results, count = get_run_script_statistics_by_month(db_session, is_user, month=month, start=start, limit=limit, order_by=order_by)
    except Exception as e:
        logger.error(e)
        logger.exception(e)
        return make_response(('Internal Server Error.', 500))
    finally:
        db_session.close()

    return make_response(({'results': results, 'count': count}, 200))


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5055), app)
    http_server.serve_forever()
