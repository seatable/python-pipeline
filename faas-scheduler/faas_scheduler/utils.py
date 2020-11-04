import os
import jwt
import time
import json
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta

from seaserv import seafile_api
from faas_scheduler.models import Task, TaskLog
from faas_scheduler.constants import CONDITION_DAILY
import faas_scheduler.settings as settings

logger = logging.getLogger(__name__)
faas_func_url = settings.FAAS_URL.rstrip('/') + '/function/run-python'


def check_auth_token(request):
    value = request.headers.get('Authorization', '')
    if value == 'Token ' + settings.AUTH_TOKEN:
        return True

    return False


def get_asset_id(repo_id, dtable_uuid, script_name):
    script_path = os.path.join(
        '/asset', str(dtable_uuid), 'scripts', script_name)
    asset_id = seafile_api.get_file_id_by_path(repo_id, script_path)

    return asset_id


def get_script_url(repo_id, asset_id, script_name):
    token = seafile_api.get_fileserver_access_token(
        repo_id, asset_id, 'download', '', use_onetime=True)
    if not token:
        return None
    script_url = '%s/files/%s/%s' % (
        settings.FILE_SERVER_ROOT.rstrip('/'), token, urllib.parse.quote(script_name))

    return script_url


def get_temp_api_token(dtable_uuid, script_name):
    temp_api_token = jwt.encode({
        'dtable_uuid': dtable_uuid,
        'app_name': script_name,
        'exp': int(time.time()) + 60 * 60,
    }, settings.DTABLE_PRIVATE_KEY, algorithm='HS256').decode()

    return temp_api_token


def call_faas_func(script_url, temp_api_token, context_data):
    response = requests.post(faas_func_url, json={
        'script_url': script_url,
        'env': {
            'dtable_web_url': settings.DTABLE_WEB_SERVICE_URL,
            'api_token': temp_api_token,
        },
        'context_data': context_data,
    })

    # No matter the success or failure of running script
    # return 200 always
    # if response status is not 200, it indicates that some internal error occurs
    if response.status_code != 200:
        logger.error('FAAS error: %d %s' % (response.status_code, response.text))
        return None

    # there is a `output`, normal output or error output, and a `return_code`, 0 success 1 fail, in response json
    # just return it
    result = response.json()

    return result


def get_task(db_session, dtable_uuid, script_name):
    task = db_session.query(
        Task).filter_by(dtable_uuid=dtable_uuid, script_name=script_name).first()

    return task


def add_task(db_session, repo_id, dtable_uuid, script_name, context_data, trigger, is_active):
    context_data = json.dumps(context_data) if context_data else None
    task = Task(
        repo_id, dtable_uuid, script_name, context_data, json.dumps(trigger), is_active)
    db_session.add(task)
    db_session.commit()

    return task


def update_task(db_session, task, context_data, trigger, is_active):
    if context_data is not None:
        task.context_data = json.dumps(context_data)
    if trigger is not None:
        task.trigger = json.dumps(trigger)
    if is_active is not None:
        task.is_active = is_active
    db_session.commit()

    return task


def delete_task(db_session, task):
    db_session.delete(task)
    db_session.commit()

    return True


def list_tasks(db_session, is_active=True):
    tasks = db_session.query(
        Task).filter_by(is_active=is_active)

    return tasks


def add_task_log(db_session, task_id):
    task_log = TaskLog(task_id, datetime.now())
    db_session.add(task_log)
    db_session.commit()

    return task_log


def update_task_log(db_session, task_log, success, return_code, output):
    task_log.finished_at = datetime.now()
    task_log.success = success
    task_log.return_code = return_code
    task_log.output = output
    db_session.commit()

    return task_log


def list_task_logs(db_session, task_id, current_page, per_page):
    start = per_page * (current_page - 1)
    task_logs = db_session.query(
        TaskLog).filter_by(task_id=task_id).offset(start).limit(per_page)

    return task_logs


def get_task_log(db_session, log_id):
    task_log = db_session.query(TaskLog).filter_by(id=log_id).first()

    return task_log


def update_task_trigger_time(db_session, task):
    task.last_trigger_time = datetime.now()
    db_session.commit()

    return task


def list_tasks_to_run(db_session):
    """ Only for scheduler """
    active_tasks = list_tasks(db_session)
    tasks = []
    now = datetime.now()
    for task in active_tasks:
        last_trigger_time = task.last_trigger_time
        trigger = json.loads(task.trigger)
        condition = trigger.get('condition')
        # if condition == CONDITION_DAILY:
        alarm_days = trigger.get('alarm_days', 1)

        if last_trigger_time == None:
            tasks.append(task)
        else:
            if last_trigger_time + timedelta(days=alarm_days) <= now:
                tasks.append(task)

    return tasks


def run_task(task):
    """ Only for scheduler """
    from faas_scheduler import DBSession
    db_session = DBSession()  # for multithreading

    task_id = task.id
    repo_id = task.repo_id
    dtable_uuid = task.dtable_uuid
    script_name = task.script_name
    context_data = json.dumps(task.context_data) if task.context_data else None

    try:
        asset_id = get_asset_id(repo_id, dtable_uuid, script_name)
        if not asset_id:
            task = get_task(db_session, dtable_uuid, script_name)
            update_task(db_session, task, None, None, False)
            raise ValueError('script not found')
        script_url = get_script_url(repo_id, asset_id, script_name)
        temp_api_token = get_temp_api_token(dtable_uuid, script_name)
        #
        task_log = add_task_log(db_session, task_id)
        result = call_faas_func(script_url, temp_api_token, context_data)

        if not result:
            success = False
            return_code = None
            output = None
        else:
            success = True
            return_code = result.get('return_code')
            output = result.get('output')
            task = get_task(db_session, dtable_uuid, script_name)
            update_task_trigger_time(db_session, task)

        update_task_log(db_session, task_log, success, return_code, output)
    except Exception as e:
        logger.exception('Run task %d error: %s' % (task_id, e))
    finally:
        db_session.close()

    return True
