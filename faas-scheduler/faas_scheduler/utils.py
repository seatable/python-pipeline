import os
import jwt
import time
import json
import requests
import urllib.parse
from datetime import datetime

from seaserv import seafile_api
from faas_scheduler.models import Task, TaskLog
import faas_scheduler.settings as settings

faas_func_url = settings.FAAS_URL.strip('/') + '/function/' + 'run-python'


def get_asset_id(repo_id, dtable_uuid, script_name):
    script_path = os.path.join(
        '/asset', str(dtable_uuid), 'scripts', script_name)
    asset_id = seafile_api.get_file_id_by_path(repo_id, script_path)
    return asset_id


def get_inner_path(repo_id, asset_id, script_name):
    token = seafile_api.get_fileserver_access_token(
        repo_id, asset_id, 'view', '', use_onetime=True)
    if not token:
        return None
    inner_path = '%s/files/%s/%s' % (
        settings.INNER_FILE_SERVER_ROOT.rstrip('/'), token, urllib.parse.quote(script_name))

    return inner_path


def get_temp_api_token(dtable_uuid, script_name):
    temp_api_token = jwt.encode({
        'dtable_uuid': dtable_uuid,
        'app_name': script_name,
        'exp': int(time.time()) + 60 * 60,
    }, settings.DTABLE_PRIVATE_KEY, algorithm='HS256').decode()

    return temp_api_token


def call_faas_func(script_url, temp_api_token):
    response = requests.post(faas_func_url, json={
        'script_url': script_url,
        'env': {
            'dtable_web_url': settings.DTABLE_WEB_SERVICE_URL,
            'api_token': temp_api_token,
        }
    })

    # No matter the success or failure of running script
    # return 200 always
    # if response status is not 200, it indicates that some internal error occurs
    if response.status_code != 200:
        return None

    # there is a `output`, normal output or error output, and a `return_code`, 0 success 1 fail, in response json
    # just return it
    result = response.json()

    return result


def get_task(db_session, dtable_uuid, script_name):
    task = db_session.query(
        Task).filter_by(dtable_uuid=dtable_uuid, script_name=script_name).first()
    return task


def add_task(db_session, repo_id, dtable_uuid, script_name, trigger, is_active):
    task = Task(repo_id, dtable_uuid, script_name,
                json.dumps(trigger), is_active)
    db_session.add(task)
    db_session.commit()
    return task


def update_task(db_session, task, trigger, is_active):
    kwargs = {}
    if trigger is not None:
        kwargs['trigger'] = json.dumps(trigger)
    if is_active is not None:
        kwargs['is_active'] = is_active
    task.update(kwargs)
    db_session.commit()
    return task


def delete_task(db_session, task):
    task.delete()
    db_session.commit()
    return True


def list_task(db_session, is_active=True):
    tasks = db_session.query(
        Task).filter_by(dis_active=is_active)
    return tasks


def add_task_log(db_session, task_id):
    task_log = TaskLog(task_id, datetime.now())
    db_session.add(task_log)
    db_session.commit()
    return task_log


def update_task_log(db_session, task_log, success, return_code, output):
    task_log.update({
        'finished_at': datetime.now(),
        'success': success,
        'return_code': return_code,
        'output': json.dumps(output) if output else None,
    })
    db_session.commit()
    return task_log


def list_task_log(db_session, task_id):
    task_logs = db_session.query(
        TaskLog).filter_by(task_id=task_id)
    return task_logs
