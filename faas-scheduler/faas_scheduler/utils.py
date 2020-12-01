import os
import jwt
import time
import json
import logging
import requests
import urllib.parse
from datetime import datetime, timedelta

from seaserv import seafile_api, ccnet_api
from faas_scheduler.models import Task, TaskLog, ScriptLog
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
    try:
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

    except Exception as e:
        logger.error(e)
        return None


def update_statistics(db_session, dtable_uuid, owner, result):
    spend_time = result.get('spend_time')
    if not spend_time:
        return

    sqls = ['''
    INSERT INTO dtable_run_script_statistics(dtable_uuid, run_date, total_run_count, total_run_time, update_at) VALUES
    (:dtable_uuid, :run_date, 1, :spend_time, :update_at)
    ON DUPLICATE KEY UPDATE
    total_run_count=total_run_count+1,
    total_run_time=total_run_time+:spend_time,
    update_at=:update_at;
    ''']

    org_id = -1
    if owner:  # maybe some old tasks without owner, so user/org statistics only for valuable owner
        if '@seafile_group' not in owner:
            orgs = ccnet_api.get_orgs_by_user(owner)
            if orgs:
                org_id = orgs[0].org_id
            else:
                org_id = -1
        else:
            group_id = owner[:owner.find('@seafile_grpup')]
            org_id = ccnet_api.get_org_id_by_group(int(group_id))

        if org_id == -1:
            sqls += ['''
            INSERT INTO user_run_script_statistics(username, run_date, total_run_count, total_run_time, update_at) VALUES
            (:username, :run_date, 1, :spend_time, :update_at)
            ON DUPLICATE KEY UPDATE
            total_run_count=total_run_count+1,
            total_run_time=total_run_time+:spend_time,
            update_at=:update_at;
            ''']
        else:
            sqls += ['''
            INSERT INTO org_run_script_statistics(org_id, run_date, total_run_count, total_run_time, update_at) VALUES
            (:org_id, :run_date, 1, :spend_time, :update_at)
            ON DUPLICATE KEY UPDATE
            total_run_count=total_run_count+1,
            total_run_time=total_run_time+:spend_time,
            update_at=:update_at;
            ''']

    try:
        for sql in sqls:
            db_session.execute(sql, {
                'dtable_uuid': dtable_uuid,
                'username': owner,
                'org_id': org_id,
                'run_date': datetime.today(),
                'spend_time': spend_time,
                'update_at': datetime.now()
            })
        db_session.commit()
    except Exception as e:
        logger.exception('update statistics sql error: %s' % (e,))


def get_task(db_session, dtable_uuid, script_name):
    task = db_session.query(
        Task).filter_by(dtable_uuid=dtable_uuid, script_name=script_name).first()

    return task


def add_task(db_session, repo_id, dtable_uuid, owner, script_name, context_data, trigger, is_active):
    context_data = json.dumps(context_data) if context_data else None
    task = Task(
        repo_id, dtable_uuid, owner, script_name, context_data, json.dumps(trigger), is_active)
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


def list_task_logs(db_session, task_id):
    task_logs = db_session.query(TaskLog).filter_by(task_id=task_id)

    return task_logs


def delete_task_logs(db_session, task_id):
    db_session.query(TaskLog).filter_by(task_id=task_id).delete()
    db_session.commit()

    return True


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
    owner = task.owner
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
        update_statistics(db_session, dtable_uuid, owner, result)

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


def get_script(db_session, script_id):
    script = db_session.query(
        ScriptLog).filter_by(id=script_id).first()

    return script


def add_script(db_session, repo_id, dtable_uuid, script_name, context_data):
    context_data = json.dumps(context_data) if context_data else None
    script = ScriptLog(
        repo_id, dtable_uuid, script_name, context_data, datetime.now())
    db_session.add(script)
    db_session.commit()

    return script


def update_script(db_session, script, success, return_code, output):
    script.finished_at = datetime.now()
    script.success = success
    script.return_code = return_code
    script.output = output
    db_session.commit()

    return script


def run_script(script_id, script_url, temp_api_token, context_data):
    """ Only for server """
    from faas_scheduler import DBSession
    db_session = DBSession()  # for multithreading

    try:
        result = call_faas_func(script_url, temp_api_token, context_data)

        if not result:
            success = False
            return_code = None
            output = None
        else:
            success = True
            return_code = result.get('return_code')
            output = result.get('output')

        script = get_script(db_session, script_id)
        update_script(db_session, script, success, return_code, output)
    except Exception as e:
        logger.exception('Run script %d error: %s' % (script_id, e))
    finally:
        db_session.close()

    return True
def get_run_script_statistics_by_month(db_session, is_user=1, month=None, start=None, limit=None, order_by=None):
    sql = '''
    SELECT {column}, SUM(total_run_count) AS total_run_count, SUM(total_run_time) AS total_run_time
    FROM {table_name}
    WHERE DATE_FORMAT(run_date, '%%Y-%%m')=DATE_FORMAT(:month, '%%Y-%%m')
    GROUP BY {column}
    %(order_by)s
    LIMIT :limit OFFSET :offset
    '''

    if not month:
        month = datetime.today()
    if is_user:
        table_name = 'user_run_script_statistics'
        column = 'username'
    else:
        table_name = 'org_run_script_statistics'
        column = 'org_id'

    sql = sql.format(table_name=table_name, column=column)

    args = {
        'month': month,
        'limit': limit,
        'offset': start,
    }
    if order_by:
        sql = sql % {'order_by': 'ORDER BY %s' % (order_by,)}
    else:
        sql = sql % {'order_by': ''}

    results = []
    for temp in db_session.execute(sql, args).fetchall():
        item = {
            'total_run_count': int(temp[1]),
            'total_run_time': temp[2]
        }
        if is_user:
            item['username'] = temp[0]
        else:
            item['org_id'] = temp[0]
        results.append(item)

    if results:
        count_sql = '''
        SELECT COUNT(1) FROM
            (SELECT DISTINCT {column} FROM {table_name}
            WHERE DATE_FORMAT(run_date, '%Y-%m')=DATE_FORMAT(:month, '%Y-%m')
            GROUP BY {column}) t
        '''
        count = db_session.execute(count_sql.format(table_name=table_name, column=column), args).fetchone()[0]
    else:
        count = 0

    return results, count
