import os
import json
import logging
import requests
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from tzlocal import get_localzone
from sqlalchemy import case, desc, func, text
from sqlalchemy.orm import load_only
from faas_scheduler.models import ScriptLog

import sys

sys.path.append("/opt/scheduler")
from database import DBSession

logger = logging.getLogger(__name__)

STARTER_URL = os.getenv("PYTHON_STARTER_URL", "")
RUN_FUNC_URL = STARTER_URL.rstrip("/") + "/function/run-python"
SEATABLE_SERVER_URL = os.getenv("SEATABLE_SERVER_URL", "")
SCHEDULER_AUTH_TOKEN = os.getenv("PYTHON_SCHEDULER_AUTH_TOKEN", "")
DELETE_LOG_DAYS = os.environ.get("DELETE_LOG_DAYS", "30")
DELETE_STATISTICS_DAYS = os.environ.get("DELETE_STATISTICS_DAYS", "90")
LOG_LEVEL = os.environ.get("PYTHON_SCHEDULER_LOG_LEVEL", "INFO")

# defaults...
LOG_DIR = "/opt/scheduler/logs/"
SUB_PROCESS_TIMEOUT = int(os.environ.get("PYTHON_PROCESS_TIMEOUT", 60 * 15))
TIMEOUT_OUTPUT = (
    "The script's running time exceeded the limit and the execution was aborted."
)
VERSION = os.getenv("VERSION")


def get_log_level(level):
    if level.lower() == "info":
        return logging.INFO
    elif level.lower() == "warning":
        return logging.WARNING
    elif level.lower() == "debug":
        return logging.DEBUG
    elif level.lower() == "error":
        return logging.ERROR
    elif level.lower() == "critical":
        return logging.CRITICAL
    return logging.INFO


def basic_log(log_file):
    if os.environ.get("LOG_TO_STDOUT", "false").lower() == "true":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
    log_level = get_log_level(LOG_LEVEL)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s %(filename)s:%(lineno)s %(funcName)s %(message)s"
    )
    handler.setFormatter(formatter)
    logging.root.setLevel(log_level)
    logging.root.addHandler(handler)


class ScriptInvalidException(Exception):
    pass


## part of ping to get the check if the python starter can be reached.
def ping_starter():
    response = requests.get(STARTER_URL.rstrip("/") + "/ping/", timeout=30)
    if response.status_code == 200:
        return True

    return False


## triggered from scheduler.py to remove old script_logs
def delete_log_after_days(db_session):
    clean_script_logs = (
        "DELETE FROM `script_log` WHERE `started_at` < DATE_SUB(NOW(), INTERVAL %s DAY)"
        % DELETE_LOG_DAYS
    )
    logger.debug(clean_script_logs)

    try:
        result = db_session.execute(text(clean_script_logs))
        db_session.commit()
        msg = "[%s] Clean %d script logs" % (datetime.now(), result.rowcount)
        logger.info(msg)
    except Exception as e:
        logger.exception(e)
    finally:
        db_session.close()


## triggered from scheduler.py to remove old statistics
def delete_statistics_after_days(db_session):
    tables = [
        "dtable_run_script_statistics",
        "org_run_script_statistics",
        "user_run_script_statistics",
    ]

    for table in tables:
        clean_statistics_logs = (
            f"DELETE FROM `{table}` WHERE `run_date` < DATE_SUB(NOW(), INTERVAL %s DAY)"
            % DELETE_STATISTICS_DAYS
        )
        logger.debug(clean_statistics_logs)

        try:
            result = db_session.execute(text(clean_statistics_logs))
            db_session.commit()
            msg = f"[{datetime.now()}] Clean {result.rowcount} script logs from {table}"
            logger.info(msg)
        except Exception as e:
            logger.exception(e)

    db_session.close()


def check_auth_token(request):
    value = request.headers.get("Authorization", "")
    if (
        value == "Token " + SCHEDULER_AUTH_TOKEN
        or value == "Bearer " + SCHEDULER_AUTH_TOKEN
    ):
        return True

    return False


def get_script_file(dtable_uuid, script_name):
    if not script_name or not dtable_uuid:
        raise ScriptInvalidException(
            "dtable: %s script: %s invalid" % (dtable_uuid, script_name)
        )
    dtable_uuid = str(UUID(dtable_uuid))
    headers = {"Authorization": "Token " + SCHEDULER_AUTH_TOKEN}
    url = "%s/api/v2.1/dtable/%s/run-script/%s/task/file/" % (
        SEATABLE_SERVER_URL.rstrip("/"),
        dtable_uuid,
        script_name,
    )
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:  # script file not found
        raise ScriptInvalidException(
            "dtable: %s, script: %s invalid" % (dtable_uuid, script_name)
        )
    if response.status_code != 200:
        logger.error(
            "Fail to get script file: %s %s, error response: %s, %s",
            dtable_uuid,
            script_name,
            response.status_code,
            response.text,
        )
        raise ValueError("script not found")

    return response.json()


# call python-starter to run the script!
def call_faas_func(script_url, temp_api_token, context_data, script_id=None):
    try:
        data = {
            "script_url": script_url,
            "env": {
                "dtable_web_url": SEATABLE_SERVER_URL.rstrip("/"),
                "api_token": temp_api_token,
            },
            "context_data": context_data,
            "script_id": script_id,
        }
        headers = {"User-Agent": "python-scheduler/" + VERSION}
        logger.debug("I call starter at url %s", RUN_FUNC_URL)
        response = requests.post(RUN_FUNC_URL, json=data, timeout=30, headers=headers)

        # script will be executed asynchronously, so there will be nothing in response
        # so only check response

        if response.status_code != 200:
            logger.error(
                "Fail to call scheduler: %s, data: %s, error response: %s, %s",
                RUN_FUNC_URL,
                data,
                response.status_code,
                response.text,
            )

    except Exception as e:
        logger.error(
            "Fail to call scheduler: %s, data: %s, error: %s", RUN_FUNC_URL, data, e
        )
        return None


def update_statistics(db_session, dtable_uuid, owner, org_id, spend_time):
    if not spend_time:
        return
    username = owner

    # dtable_run_script_statistcis
    sqls = [
        """
    INSERT INTO dtable_run_script_statistics(dtable_uuid, run_date, total_run_count, total_run_time, update_at) VALUES
    (:dtable_uuid, :run_date, 1, :spend_time, :update_at)
    ON DUPLICATE KEY UPDATE
    total_run_count=total_run_count+1,
    total_run_time=total_run_time+:spend_time,
    update_at=:update_at;
    """
    ]

    # org_run_script_statistics
    if org_id and org_id != -1:
        sqls += [
            """
        INSERT INTO org_run_script_statistics(org_id, run_date, total_run_count, total_run_time, update_at) VALUES
        (:org_id, :run_date, 1, :spend_time, :update_at)
        ON DUPLICATE KEY UPDATE
        total_run_count=total_run_count+1,
        total_run_time=total_run_time+:spend_time,
        update_at=:update_at;
        """
        ]

    # user_run_script_statistics
    if "@seafile_group" not in username:
        sqls += [
            """
        INSERT INTO user_run_script_statistics(username, org_id, run_date, total_run_count, total_run_time, update_at) VALUES
        (:username, :org_id, :run_date, 1, :spend_time, :update_at)
        ON DUPLICATE KEY UPDATE
        org_id=:org_id,
        total_run_count=total_run_count+1,
        total_run_time=total_run_time+:spend_time,
        update_at=:update_at;
        """
        ]

    try:
        for sql in sqls:
            db_session.execute(
                text(sql),
                {
                    "dtable_uuid": dtable_uuid,
                    "username": username,
                    "org_id": org_id,
                    "run_date": datetime.today(),
                    "spend_time": spend_time,
                    "update_at": datetime.now(),
                },
            )
        db_session.commit()
    except Exception as e:
        logger.exception("update statistics sql error: %s", e)


# required to get "script logs" in dtable-web
def list_task_logs(db_session, dtable_uuid, script_name, order_by="-id"):
    if "-" in order_by:
        order_by = desc(order_by.strip("-"))
    task_logs = (
        db_session.query(ScriptLog)
        .filter_by(dtable_uuid=dtable_uuid, script_name=script_name)
        .order_by(order_by)
    )

    return task_logs


# required for get "script logs" in dtable-web
def get_task_log(db_session, log_id):
    task_log = db_session.query(ScriptLog).filter_by(id=log_id).first()
    return task_log


# get current count of executions for team or username
def get_run_scripts_count_monthly(username, org_id, db_session, month=None):
    sql = """
    SELECT SUM(total_run_count) FROM %s
    WHERE DATE_FORMAT(run_date, '%%Y-%%m')=:month
    AND %s=:owner_username
    """
    if org_id and org_id != -1:
        sql = sql % ("org_run_script_statistics", "org_id")
        owner_username = org_id
    else:
        sql = sql % ("user_run_script_statistics", "username")
        owner_username = username
    if not month:
        month = datetime.strftime(datetime.now(), "%Y-%m")
    count = db_session.execute(
        text(sql), {"month": month, "owner_username": owner_username}
    ).fetchone()[0]
    return int(count) if count else 0


## executed from flask_server, to check if execution is possible (check limits!)
def can_run_task(owner, org_id, db_session, scripts_running_limit=None):
    """
    whether can run task (check run limits for teams)
    """
    if org_id == -1 and "@seafile_group" in owner:
        return True

    # check run-scripts count/limit
    if not scripts_running_limit:
        url = "%s/api/v2.1/scripts-running-limit/" % (SEATABLE_SERVER_URL.strip("/"),)
        headers = {"Authorization": "Token " + SCHEDULER_AUTH_TOKEN}
        if org_id and org_id != -1:
            params = {"org_id": org_id}
        elif owner:
            params = {"username": owner}
        else:
            return True
        scripts_running_limit = -1
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except Exception as e:
            logger.error("request run-scripts-limit error: %s", e)
            return False
        if response.status_code != 200:
            logger.error(
                "request run-scripts-limit error response status code: %s",
                response.status_code,
            )
            return False
        scripts_running_limit = response.json()["scripts_running_limit"]
    if scripts_running_limit == -1:  # no limit
        return True

    count = get_run_scripts_count_monthly(owner, org_id, db_session)
    return count < scripts_running_limit


# update entries in script_log after SUB_PROCESS_TIMEOUT (typically 15 minutes)
def check_and_set_tasks_timeout(db_session):
    now = datetime.now()
    sql = """
        UPDATE script_log SET success=0, return_code=-1, output=:timeout_output, finished_at=:now
        WHERE success IS NULL AND TIMESTAMPDIFF(SECOND, started_at, :now) > :timeout_interval
    """
    try:
        db_session.execute(
            text(sql),
            {
                "now": now,
                "timeout_interval": SUB_PROCESS_TIMEOUT,
                "timeout_output": TIMEOUT_OUTPUT,
            },
        )
        db_session.commit()
    except Exception as e:
        logger.exception(e)


def get_script(db_session, script_id):
    script = db_session.query(ScriptLog).filter_by(id=script_id).first()

    return script


def add_script(
    db_session,
    dtable_uuid,
    owner,
    org_id,
    script_name,
    context_data,
    operate_from="manualy",
):
    context_data = json.dumps(context_data) if context_data else None
    script = ScriptLog(
        dtable_uuid,
        owner,
        org_id,
        script_name,
        context_data,
        datetime.now(),
        operate_from,
    )
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


# run_script is called from flash_server. Initializes the process.
def run_script(
    script_id, dtable_uuid, script_name, script_url, temp_api_token, context_data
):
    """Only for flask-server"""
    # from faas_scheduler import DBSession
    db_session = DBSession()  # for multithreading

    try:
        if not script_url:
            script_file = get_script_file(dtable_uuid, script_name)
            script_url = script_file.get("script_url", "")
        logger.debug("run_script executed...")
        call_faas_func(script_url, temp_api_token, context_data, script_id=script_id)
    except Exception as e:
        logger.exception("Run script %d error: %s", script_id, e)
    finally:
        db_session.close()

    return True


def hook_update_script(db_session, script_id, success, return_code, output, spend_time):
    script = db_session.query(ScriptLog).filter_by(id=script_id).first()
    if script:
        update_script(db_session, script, success, return_code, output)
        update_statistics(
            db_session, script.dtable_uuid, script.owner, script.org_id, spend_time
        )


def get_run_script_statistics_by_month(
    db_session, target, month=None, start=0, limit=25, order_by=None, direction=None
):
    sql = """
    SELECT {column}, SUM(total_run_count) AS total_run_count, SUM(total_run_time) AS total_run_time
    FROM {table_name}
    WHERE DATE_FORMAT(run_date, '%%Y-%%m')=DATE_FORMAT(:month, '%%Y-%%m')
    GROUP BY {column}
    %(order_by)s
    LIMIT :limit OFFSET :offset
    """

    if not month:
        month = datetime.today()

    if target == "user":
        table_name = "user_run_script_statistics"
        column = "username"
    elif target == "org":
        table_name = "org_run_script_statistics"
        column = "org_id"
    elif target == "base":
        table_name = "dtable_run_script_statistics"
        column = "dtable_uuid"
    else:
        return []

    sql = sql.format(table_name=table_name, column=column)
    args = {
        "month": month,
        "limit": limit,
        "offset": start,
    }
    if order_by:
        if direction == "desc":
            sql = sql % {"order_by": "ORDER BY %s DESC" % (order_by,)}
        else:
            sql = sql % {"order_by": "ORDER BY %s" % (order_by,)}
    else:
        sql = sql % {"order_by": ""}

    results = []
    for temp in db_session.execute(text(sql), args).fetchall():
        item = {"total_run_count": int(temp[1]), "total_run_time": int(temp[2])}
        if target == "user":
            item["username"] = temp[0]
        elif target == "org":
            item["org_id"] = temp[0]
        elif target == "base":
            item["base_uuid"] = temp[0]
        results.append(item)

    if results:
        count_sql = """
        SELECT COUNT(1) FROM
            (SELECT DISTINCT {column} FROM {table_name}
            WHERE DATE_FORMAT(run_date, '%Y-%m')=DATE_FORMAT(:month, '%Y-%m')
            GROUP BY {column}) t
        """
        count_sql = count_sql.format(table_name=table_name, column=column)
        total_count = db_session.execute(text(count_sql), args).fetchone()[0]
    else:
        total_count = 0

    return month.strftime("%Y-%m"), total_count, results


def get_script_runs(
    db_session, org_id, base_uuid, start, end, page, per_page
) -> Tuple[List[ScriptLog], int]:
    fields = [
        ScriptLog.id,
        ScriptLog.dtable_uuid,
        ScriptLog.owner,
        ScriptLog.org_id,
        ScriptLog.script_name,
        ScriptLog.started_at,
        ScriptLog.finished_at,
        ScriptLog.success,
        ScriptLog.return_code,
        ScriptLog.operate_from,
    ]
    query = db_session.query(ScriptLog).options(load_only(*fields))

    if org_id:
        query = query.filter_by(org_id=org_id)

    if base_uuid:
        query = query.filter_by(dtable_uuid=base_uuid)

    if start:
        query = query.filter(ScriptLog.started_at >= start)

    if end:
        query = query.filter(ScriptLog.started_at <= end)

    total_count = query.count()
    runs = query.limit(per_page).offset((page - 1) * per_page).all()

    return runs, total_count


def get_statistics_grouped_by_base(
    db_session,
    org_id: int,
    start: Optional[datetime],
    end: Optional[datetime],
    page: int,
    per_page: int,
) -> Tuple[List[dict], int]:
    # pylint: disable=E1102
    # False positive caused by https://github.com/pylint-dev/pylint/issues/8138

    fields = [
        ScriptLog.dtable_uuid,
        func.count(ScriptLog.id).label("number_of_runs"),
        # This calls MariaDB's TIMESTAMPDIFF() function with microsecond precision to prevent rounding errors
        # Note: Scripts that haven't finished yet are simply ignored
        func.sum(
            func.timestampdiff(
                text("MICROSECOND"), ScriptLog.started_at, ScriptLog.finished_at
            )
            / 1_000_000
        ).label("total_run_time"),
        func.count(case((ScriptLog.operate_from == "manualy", 1))).label(
            "triggered_manually"
        ),
        func.count(case((ScriptLog.operate_from == "automation-rule", 1))).label(
            "triggered_by_automation_rule"
        ),
        func.count(case((ScriptLog.success == True, 1))).label("successful_runs"),
        func.count(case((ScriptLog.success == False, 1))).label("unsuccessful_runs"),
    ]

    query = (
        db_session.query(*fields)
        .filter_by(org_id=org_id)
        .group_by(ScriptLog.dtable_uuid)
    )

    if start:
        query = query.filter(ScriptLog.started_at >= start)

    if end:
        query = query.filter(ScriptLog.started_at <= end)

    total_count = query.count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()

    results = []

    for row in rows:
        results.append(
            {
                "base_uuid": row.dtable_uuid,
                "number_of_runs": row.number_of_runs,
                # int() is required since MariaDB returns total_run_time as a string
                "total_run_time": int(row.total_run_time),
                "triggered_manually": row.triggered_manually,
                "triggered_by_automation_rule": row.triggered_by_automation_rule,
                "successful_runs": row.successful_runs,
                "unsuccessful_runs": row.unsuccessful_runs,
            }
        )

    return results, total_count


def get_statistics_grouped_by_day(
    db_session,
    org_id: int,
    base_uuid: Optional[str],
    start: Optional[datetime],
    end: Optional[datetime],
    page: int,
    per_page: int,
) -> Tuple[List[dict], int]:
    # pylint: disable=E1102
    # False positive caused by https://github.com/pylint-dev/pylint/issues/8138

    fields = [
        func.date(ScriptLog.started_at).label("date"),
        func.count(ScriptLog.id).label("number_of_runs"),
        # This calls MariaDB's TIMESTAMPDIFF() function with microsecond precision to prevent rounding errors
        # Note: Scripts that haven't finished yet are simply ignored
        func.sum(
            func.timestampdiff(
                text("MICROSECOND"), ScriptLog.started_at, ScriptLog.finished_at
            )
            / 1_000_000
        ).label("total_run_time"),
        func.count(case((ScriptLog.operate_from == "manualy", 1))).label(
            "triggered_manually"
        ),
        func.count(case((ScriptLog.operate_from == "automation-rule", 1))).label(
            "triggered_by_automation_rule"
        ),
        func.count(case((ScriptLog.success == True, 1))).label("successful_runs"),
        func.count(case((ScriptLog.success == False, 1))).label("unsuccessful_runs"),
    ]

    query = (
        db_session.query(*fields)
        .filter_by(org_id=org_id)
        .group_by(func.date(ScriptLog.started_at))
    )

    if base_uuid:
        query = query.filter(ScriptLog.dtable_uuid == base_uuid)

    if start:
        query = query.filter(ScriptLog.started_at >= start)

    if end:
        query = query.filter(ScriptLog.started_at <= end)

    total_count = query.count()
    rows = query.limit(per_page).offset((page - 1) * per_page).all()

    results = []

    for row in rows:
        results.append(
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "number_of_runs": row.number_of_runs,
                # int() is required since MariaDB returns total_run_time as a string
                "total_run_time": int(row.total_run_time),
                "triggered_manually": row.triggered_manually,
                "triggered_by_automation_rule": row.triggered_by_automation_rule,
                "successful_runs": row.successful_runs,
                "unsuccessful_runs": row.unsuccessful_runs,
            }
        )

    return results, total_count


def datetime_to_isoformat_timestr(datetime_obj):
    if not datetime_obj:
        return ""
    try:
        datetime_obj = datetime_obj.replace(microsecond=0)
        current_timezone = get_localzone()
        localized_datetime = datetime_obj.astimezone(current_timezone)
        isoformat_timestr = localized_datetime.isoformat()
        return isoformat_timestr
    except Exception as e:
        logger.error(e)
        return ""


def uuid_str_to_32_chars(uuid_str):
    return uuid_str.replace("-", "")


def uuid_str_to_36_chars(uuid_str):
    return str(UUID(uuid_str))
