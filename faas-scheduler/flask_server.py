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
from faas_scheduler.utils import check_auth_token, \
    add_task, get_task, update_task, delete_task, list_task_logs, \
    get_task_log, run_script, get_script, add_script, delete_task_logs, \
    get_run_script_statistics_by_month, hook_update_script, hook_update_task_log, \
    can_run_task, get_run_scripts_count_monthly, list_tasks, list_tasks_by_page

app = Flask(__name__)
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s'
)
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

    dtable_uuid = data.get('dtable_uuid')
    script_name = data.get('script_name')
    context_data = data.get('context_data')
    owner = data.get('owner')
    org_id = data.get('org_id')
    script_url = data.get('script_url')
    temp_api_token = data.get('temp_api_token')
    scripts_running_limit = data.get('scripts_running_limit', -1)
    if not dtable_uuid \
            or not script_name \
            or not owner \
            or not script_url:
        return make_response(('Parameters invalid', 400))

    # main
    db_session = DBSession()
    try:
        if scripts_running_limit != -1 and not can_run_task(owner, org_id, db_session, scripts_running_limit=scripts_running_limit):
            return make_response(('The number of runs exceeds the limit'), 400)
        script = add_script(db_session, dtable_uuid, owner, org_id, script_name, context_data)
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

    dtable_uuid = data.get('dtable_uuid')
    script_name = data.get('script_name')
    context_data = data.get('context_data')
    trigger = data.get('trigger')
    is_active = data.get('is_active', True)
    owner = data.get('owner')
    org_id = data.get('org_id')
    if not dtable_uuid \
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
            db_session, dtable_uuid, owner, org_id, script_name, context_data, trigger, is_active)
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
        order_by = request.args.get('org_by', '-id')
    except ValueError:
        current_page = 1
        per_page = 20

    if order_by.strip('-') not in ('id',):
        return make_response(('order_by invalid.', 400))

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

        task_logs = list_task_logs(db_session, task.id, order_by)
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


@app.route('/scripts-running-count/', methods=['GET'])
def scripts_running_count():
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))
    username = request.args.get('username')
    org_id = request.args.get('org_id')
    raw_month = request.args.get('month')
    if raw_month:
        try:
            month = datetime.strptime(raw_month, '%Y-%m').strftime('%Y-%m')
        except:
            return make_response(('month invalid.', 400))
    else:
        month = None

    if not username and not org_id:
        return make_response(('username or org_id invalid.', 400))

    if org_id:
        try:
            org_id = int(org_id)
        except:
            return make_response(('org_id invalid.', 400))
        if org_id == -1:
            return make_response(('org_id invalid.', 400))

    db_session = DBSession()
    try:
        count = get_run_scripts_count_monthly(username, org_id, db_session, month=month)
    except Exception as e:
        logger.error(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()

    return make_response(({'count': count}, 200))


@app.route('/script-result/', methods=['POST'])
def record_script_result():
    """
    Receive result of script from python-runner
    """
    try:
        data = request.get_json()
    except:
        return make_response('Bad Request.', 400)
    success = data.get('success', False)
    return_code = data.get('return_code')
    output = data.get('output')
    spend_time = data.get('spend_time')
    script_id, task_log_id = data.get('script_id'), data.get('task_log_id')

    db_session = DBSession()

    # udpate script/task log and run-time statistics
    try:
        if script_id:
            hook_update_script(db_session, script_id, success, return_code, output, spend_time)
        elif task_log_id:
            hook_update_task_log(db_session, task_log_id, success, return_code, output, spend_time)
    except Exception as e:
        logger.exception(e)
        return make_response(('Internal server error', 500))
    finally:
        db_session.close()

    return 'success'


def get_scripts_running_statistics_by_request(request, is_user=True):
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
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
    except:
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


@app.route('/admin/statistics/scripts-running/by-user/', methods=['GET'])
def user_run_python_statistics():
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    return get_scripts_running_statistics_by_request(request, is_user=True)


@app.route('/admin/statistics/scripts-running/by-org/', methods=['GET'])
def org_run_python_statistics():
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    return get_scripts_running_statistics_by_request(request, is_user=False)


@app.route('/admin/tasks/', methods=['GET'])
def time_run_task():
    if not check_auth_token(request):
        return make_response(('Forbidden', 403))

    try:
        current_page = int(request.args.get('current_page', 1))
        per_page = int(request.args.get('per_page', 25))
    except ValueError:
        current_page, per_page = 1, 25

    start = (current_page - 1) * per_page
    end = start + per_page
    db_session = DBSession()

    try:
        tasks_info = list_tasks_by_page(db_session, start, end)
    except Exception as e:
        logger.error(e)
        logger.exception(e)
        return make_response(('Internal Server Error.', 500))
    finally:
        db_session.close()

    tasks, tasks_count = tasks_info
    if tasks_count > end:
        has_next_page = True
    else:
        has_next_page = False
    page_info = {
        'has_next_page': has_next_page,
        'current_page': current_page
    }
    results = [task.to_dict() for task in tasks], page_info

    return make_response(({'results': results}, 200))


if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', 5055), app)
    http_server.serve_forever()
