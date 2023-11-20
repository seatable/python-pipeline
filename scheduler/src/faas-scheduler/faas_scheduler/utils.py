import json
import logging
import requests
from datetime import datetime, timedelta
from uuid import UUID

from tzlocal import get_localzone
from sqlalchemy import desc, distinct, text
from faas_scheduler.models import Task, ScriptLog
#from faas_scheduler.constants import CONDITION_DAILY, TIMEOUT_OUTPUT


logger = logging.getLogger(__name__)

STARTER_URL = os.getenv('PYTHON_STARTER_URL', '')
RUN_FUNC_URL = STARTER_URL.rstrip('/') + '/function/run-python'
SEATABLE_SERVER_URL = os.getenv('SEATABLE_SERVER_URL', '')
SCHEDULER_AUTH_TOKEN = os.getenv('SCHEDULER_AUTH_TOKEN', '')

# defaults...
SCRIPT_WORKERS = 5
SCHEDULER_INTERVAL = 3600
SCHEDULER_WORKERS = 3
CONF_DIR = '/opt/seatable-faas-scheduler/conf/'
LOG_DIR = '/opt/seatable-faas-scheduler/logs/'
SUB_PROCESS_TIMEOUT = 60 * 15
CONDITION_DAILY = 'daily'
TIMEOUT_OUTPUT = 'Script running for too long time!'


class ScriptInvalidException(Exception):
    pass

def ping_starter(request):
    response = requests.get(STARTER_URL.rstrip('/') + '/ping/')
    if response.status_code == 200:
        return True

    return False


def check_auth_token(request):
    value = request.headers.get('Authorization', '')
    if value == 'Token ' + SCHEDULER_AUTH_TOKEN or value == 'Bearer ' + SCHEDULER_AUTH_TOKEN:
        return True

    return False


def get_script_file(dtable_uuid, script_name):
    if not script_name or not dtable_uuid:
        raise ScriptInvalidException('dtable: %s script: %s invalid' % (dtable_uuid, script_name))
    dtable_uuid = str(UUID(dtable_uuid))
    headers = {'Authorization': 'Token ' + SCHEDULER_AUTH_TOKEN}
    url = '%s/api/v2.1/dtable/%s/run-script/%s/task/file/' % (SEATABLE_SERVER_URL.rstrip('/'), dtable_uuid, script_name)
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:  # script file not found
        raise ScriptInvalidException('dtable: %s, script: %s invalid' % (dtable_uuid, script_name))
    if response.status_code != 200:
        logger.error('Fail to get script file: %s %s, error response: %s, %s' % (dtable_uuid, script_name, response.status_code, response.text))
        raise ValueError('script not found')

    return response.json()


def call_faas_func(script_url, temp_api_token, context_data, script_id=None):
    try:
        data = {
            'script_url': script_url,
            'env': {
                'dtable_web_url': SEATABLE_SERVER_URL.rstrip('/'),
                'api_token': temp_api_token,
            },
            'context_data': context_data,
            'script_id': script_id,
        }
        response = requests.post(RUN_FUNC_URL, json=data, timeout=30)

        # script will be executed asynchronously, so there will be nothing in response
        # so only check response

        if response.status_code != 200:
            logger.error('Fail to call scheduler: %s, data: %s, error response: %s, %s', RUN_FUNC_URL, data, response.status_code, response.text)

    except Exception as e:
        logger.error('Fail to call scheduler: %s, data: %s, error: %s', RUN_FUNC_URL, data, e)
        return None


def update_statistics(db_session, dtable_uuid, owner, org_id, spend_time):
    if not spend_time:
        return
    username = owner
    sqls = ['''
    INSERT INTO dtable_run_script_statistics(dtable_uuid, run_date, total_run_count, total_run_time, update_at) VALUES
    (:dtable_uuid, :run_date, 1, :spend_time, :update_at)
    ON DUPLICATE KEY UPDATE
    total_run_count=total_run_count+1,
    total_run_time=total_run_time+:spend_time,
    update_at=:update_at;
    ''']

    if owner:  # maybe some old tasks without owner, so user/org statistics only for valuable owner

        if org_id and org_id != -1:  # org
            sqls += ['''
            INSERT INTO org_run_script_statistics(org_id, run_date, total_run_count, total_run_time, update_at) VALUES
            (:org_id, :run_date, 1, :spend_time, :update_at)
            ON DUPLICATE KEY UPDATE
            total_run_count=total_run_count+1,
            total_run_time=total_run_time+:spend_time,
            update_at=:update_at;
            ''']

        elif org_id and org_id == -1 and '@seafile_group' not in username:      # user who is not an org user
            sqls += ['''
            INSERT INTO user_run_script_statistics(username, run_date, total_run_count, total_run_time, update_at) VALUES
            (:username, :run_date, 1, :spend_time, :update_at)
            ON DUPLICATE KEY UPDATE
            total_run_count=total_run_count+1,
            total_run_time=total_run_time+:spend_time,
            update_at=:update_at;
            ''']

    try:
        for sql in sqls:
            db_session.execute(text(sql), {
                'dtable_uuid': dtable_uuid,
                'username': username,
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


def add_task(db_session, dtable_uuid, owner, org_id, script_name, context_data, trigger, is_active):
    context_data = json.dumps(context_data) if context_data else None
    task = Task(
        dtable_uuid, owner, org_id, script_name, context_data, json.dumps(trigger), is_active)
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


def get_run_scripts_count_monthly(username, org_id, db_session, month=None):
    sql = '''
    SELECT SUM(total_run_count) FROM %s
    WHERE DATE_FORMAT(run_date, '%%Y-%%m')=:month
    AND %s=:owner_username
    '''
    if org_id and org_id != -1:
        sql = sql % ('org_run_script_statistics', 'org_id')
        owner_username = org_id
    else:
        sql = sql % ('user_run_script_statistics', 'username')
        owner_username = username
    if not month:
        month = datetime.strftime(datetime.now(), '%Y-%m')
    else:
        month = month
    count = db_session.execute(text(sql), {
        'month': month,
        'owner_username': owner_username
    }).fetchone()[0]
    return int(count) if count else 0


def can_run_task(owner, org_id, db_session, scripts_running_limit=None):
    """
    whether can run task
    """
    if org_id == -1 and '@seafile_group' in owner:
        return True

    # check run-scripts count/limit
    if not scripts_running_limit:
        url = '%s/api/v2.1/scripts-running-limit/' % (SEATABLE_SERVER_URL.strip('/'),)
        headers = {'Authorization': 'Token ' + SCHEDULER_AUTH_TOKEN}
        if org_id and org_id != -1:
            params = {'org_id': org_id}
        elif owner:
            params = {'username': owner}
        else:
            return True
        scripts_running_limit = -1
        try:
            response = requests.get(url, headers=headers, params=params)
        except Exception as e:
            logger.error('request run-scripts-limit error: %s', e)
            return False
        if response.status_code != 200:
            logger.error('request run-scripts-limit error response status code: %s', response.status_code)
            return False
        scripts_running_limit = response.json()['scripts_running_limit']
    if scripts_running_limit == -1:  # no limit
        return True

    count = get_run_scripts_count_monthly(owner, org_id, db_session)
    return count < scripts_running_limit


def run_task(task):
    """ Only for scheduler """
    from faas_scheduler import DBSession
    db_session = DBSession()  # for multithreading

    task_id = task.id
    dtable_uuid = task.dtable_uuid
    script_name = task.script_name
    context_data = json.dumps(task.context_data) if task.context_data else None

    try:
        if not can_run_task(task.owner, task.org_id, db_session):
            return True
        script_file = get_script_file(dtable_uuid, script_name)
        script_url = script_file.get('script_url', '')
        temp_api_token = script_file.get('temp_api_token', '')
        if not script_url:
            raise ValueError('script not found')

        #
        task_log = add_task_log(db_session, task_id)
        call_faas_func(script_url, temp_api_token, context_data, script_id=task_log.id)
        task = get_task(db_session, dtable_uuid, script_name)
        update_task_trigger_time(db_session, task)

    except ScriptInvalidException as e:
        logger.info('task: %s script: %s invalid info: %s', task.id, task.script_name, e)
        db_session.query(Task).filter(Task.id==task.id).delete()
        db_session.commit()

    except Exception as e:
        logger.exception('Run task %d error: %s' % (task_id, e))
    finally:
        db_session.close()

    return True


def remove_invalid_tasks(db_session):
    try:
        # select all users and org_ids
        users = [t[0] for t in db_session.query(distinct(Task.owner)).filter(Task.org_id==-1)]
        org_ids = [t[0] for t in db_session.query(distinct(Task.org_id)).filter(Task.org_id!=-1)]

        # request user/org script/task permissions
        permission_url = SEATABLE_SERVER_URL.strip('/')+ '/api/v2.1/script-permissions/'
        headers = {'Authorization': 'Token ' + SCHEDULER_AUTH_TOKEN}
        response = requests.get(permission_url, headers=headers, json={'users': users, 'org_ids': org_ids})
        if response.status_code != 200:
            logger.error('request script permissions error status code: %s', response.status_code)
            return

        # retrieve user/org permissions from response
        user_script_permissions = response.json().get('user_script_permissions', {})
        org_script_permissions = response.json().get('org_script_permissions', {})

        # remove tasks that belong to owner/org who has no permission to run task
        # and their logs
        task_ids = []
        for user, permission_dict in user_script_permissions.items():
            if permission_dict.get('can_schedule_run_script') is False:
                tasks = db_session.query(Task).filter_by(owner=user)
                for task in tasks:
                    task_ids.append(task.id)
                tasks.delete()
        for org_id, permission_dict in org_script_permissions.items():
            if permission_dict.get('can_schedule_run_script') is False:
                tasks = db_session.query(Task).filter_by(org_id=org_id)
                for task in tasks:
                    task_ids.append(task.id)
                tasks.delete()

        db_session.commit()
    except Exception as e:
        logger.exception(e)


def check_and_set_tasks_timeout(db_session):
    now = datetime.now()
    sql = '''
        UPDATE script_log SET success=0, return_code=-1, output=:timeout_output, finished_at=:now
        WHERE success IS NULL AND TIMESTAMPDIFF(SECOND, started_at, :now) > :timeout_interval
    '''
    try:
        db_session.execute(text(sql), {
            'now': now,
            'timeout_interval': SUB_PROCESS_TIMEOUT,
            'timeout_output': TIMEOUT_OUTPUT
        })
        db_session.commit()
    except Exception as e:
        logger.exception(e)


def get_script(db_session, script_id):
    script = db_session.query(
        ScriptLog).filter_by(id=script_id).first()

    return script


def add_script(db_session, dtable_uuid, owner, org_id, script_name, context_data, operate_from='manualy'):
    context_data = json.dumps(context_data) if context_data else None
    script = ScriptLog(
        dtable_uuid, owner, org_id, script_name, context_data, datetime.now(), operate_from)
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


def run_script(script_id, dtable_uuid, script_name, script_url, temp_api_token, context_data):
    """ Only for flask-server """
    from faas_scheduler import DBSession
    db_session = DBSession()  # for multithreading

    try:
        if not script_url:
            script_file = get_script_file(dtable_uuid, script_name)
            script_url = script_file.get('script_url', '')
        call_faas_func(script_url, temp_api_token, context_data, script_id=script_id)
    except Exception as e:
        logger.exception('Run script %d error: %s' % (script_id, e))
    finally:
        db_session.close()

    return True


def hook_update_script(db_session, script_id, success, return_code, output, spend_time):
    script = db_session.query(ScriptLog).filter_by(id=script_id).first()
    if script:
        update_script(db_session, script, success, return_code, output)
        update_statistics(db_session, script.dtable_uuid, script.owner, script.org_id, spend_time)


def get_run_script_statistics_by_month(db_session, is_user=True, month=None, start=0, limit=25, order_by=None):
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
    for temp in db_session.execute(text(sql), args).fetchall():
        item = {
            'total_run_count': int(temp[1]),
            'total_run_time': int(temp[2])
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
        count_sql = count_sql.format(table_name=table_name, column=column)
        count = db_session.execute(text(count_sql), args).fetchone()[0]
    else:
        count = 0

    return results, count

def datetime_to_isoformat_timestr(datetime):
    if not datetime:
        return ''
    try:
        datetime = datetime.replace(microsecond=0)
        current_timezone = get_localzone()
        localized_datetime = datetime.astimezone(current_timezone)
        isoformat_timestr = localized_datetime.isoformat()
        return isoformat_timestr
    except Exception as e:
        logger.error(e)
        return ''
