import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from tzlocal import get_localzone
from sqlalchemy import case, desc, func, text, and_
from sqlalchemy.orm import load_only
from faas_scheduler.models import (
    ScriptLog,
    UserRunScriptStatistics,
    OrgRunScriptStatistics,
    DTableRunScriptStatistics,
)

import sys

sys.path.append("/opt/scheduler")

logger = logging.getLogger(__name__)

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


class RunScriptError(Exception):
    pass


class SendExceededNotificationsError(Exception):
    pass


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


def update_running_scripts_timeout(db_session):
    deadline = datetime.now() - timedelta(seconds=SUB_PROCESS_TIMEOUT)
    updated_count = (
        db_session.query(ScriptLog)
        .filter(
            and_(
                ScriptLog.started_at.isnot(None),
                ScriptLog.started_at <= deadline,
                ScriptLog.state == ScriptLog.RUNNING,
            )
        )
        .update(
            {
                ScriptLog.output: "timeout",
                ScriptLog.return_code: -1,
                ScriptLog.success: False,
                ScriptLog.finished_at: datetime.now(),
                ScriptLog.state: "finished",
            },
            synchronize_session=False,
        )
    )

    db_session.commit()

    logger.info("updated %s script logs", updated_count)


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


def update_stats(db_session, dtable_uuid, owner, org_id, spend_time):
    run_date = datetime.today().strftime("%Y-%m-%d")
    try:
        dtable_stats = (
            db_session.query(DTableRunScriptStatistics)
            .filter_by(dtable_uuid=dtable_uuid, run_date=run_date)
            .first()
        )
        if not dtable_stats:
            dtable_stats = DTableRunScriptStatistics(
                dtable_uuid=dtable_uuid,
                run_date=run_date,
                total_run_count=1,
                total_run_time=spend_time,
                update_at=datetime.now(),
            )
            db_session.add(dtable_stats)
        else:
            db_session.query(DTableRunScriptStatistics).filter_by(
                dtable_uuid=dtable_uuid, run_date=run_date
            ).update(
                {
                    DTableRunScriptStatistics.total_run_time: DTableRunScriptStatistics.total_run_time
                    + spend_time,
                    DTableRunScriptStatistics.total_run_count: DTableRunScriptStatistics.total_run_count
                    + 1,
                    DTableRunScriptStatistics.update_at: datetime.now(),
                }
            )
        if "@seafile_group" not in owner:
            user_stats = (
                db_session.query(UserRunScriptStatistics)
                .filter_by(username=owner, run_date=run_date)
                .first()
            )
            if not user_stats:
                user_stats = UserRunScriptStatistics(
                    username=owner,
                    org_id=org_id,
                    run_date=run_date,
                    total_run_count=1,
                    total_run_time=spend_time,
                    update_at=datetime.now(),
                )
                db_session.add(user_stats)
            else:
                db_session.query(UserRunScriptStatistics).filter_by(
                    username=owner, run_date=run_date
                ).update(
                    {
                        UserRunScriptStatistics.total_run_time: UserRunScriptStatistics.total_run_time
                        + spend_time,
                        UserRunScriptStatistics.total_run_count: UserRunScriptStatistics.total_run_count
                        + 1,
                        UserRunScriptStatistics.update_at: datetime.now(),
                    }
                )
        if org_id and org_id != -1:
            org_stats = (
                db_session.query(OrgRunScriptStatistics)
                .filter_by(org_id=org_id, run_date=run_date)
                .first()
            )
            if not org_stats:
                org_stats = OrgRunScriptStatistics(
                    org_id=org_id,
                    run_date=run_date,
                    total_run_count=1,
                    total_run_time=spend_time,
                    update_at=datetime.now(),
                )
                db_session.add(org_stats)
            else:
                db_session.query(OrgRunScriptStatistics).filter_by(
                    org_id=org_id, run_date=run_date
                ).update(
                    {
                        OrgRunScriptStatistics.total_run_time: OrgRunScriptStatistics.total_run_time
                        + spend_time,
                        OrgRunScriptStatistics.total_run_count: OrgRunScriptStatistics.total_run_count
                        + 1,
                        OrgRunScriptStatistics.update_at: datetime.now(),
                    }
                )
        db_session.commit()
    except Exception as e:
        logger.exception(
            "update stats for org_id %s owner %s dtable %s run time error %s",
            org_id,
            owner,
            dtable_uuid,
            e,
        )


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
        ScriptLog.PENDING,
        datetime.now(),
        operate_from,
    )
    db_session.add(script)
    db_session.commit()

    # update_stats_run_count(db_session, dtable_uuid, owner, org_id)

    return script


def update_script_running(db_session, started_at, script):
    script.started_at = started_at
    script.state = ScriptLog.RUNNING
    db_session.commit()


def update_script(
    db_session, script, success, return_code, output, started_at, finished_at
):
    script.started_at = started_at
    script.finished_at = finished_at
    script.success = success
    script.return_code = return_code
    script.output = output
    script.state = ScriptLog.FINISHED
    db_session.commit()

    return script


def on_script_done_update(
    db_session, script_id, success, return_code, output, started_at, spend_time
):
    script = db_session.query(ScriptLog).filter_by(id=script_id).first()
    if script:
        finished_at = started_at + timedelta(seconds=spend_time)
        update_script(
            db_session, script, success, return_code, output, started_at, finished_at
        )
        update_stats(
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
    query = (
        db_session.query(ScriptLog)
        .options(load_only(*fields))
        .order_by(ScriptLog.id.desc())
    )

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


def send_exceeded_notifications(org_ids, owners):
    url = f"{SEATABLE_SERVER_URL.strip('/')}/api/v2.1/scripts-exceeded-notifications/"
    headers = {"Authorization": f"Token {SCHEDULER_AUTH_TOKEN}"}
    data = {}
    if org_ids:
        data["org_ids"] = org_ids
    if owners:
        data["owners"] = owners
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    if not resp.ok:
        raise SendExceededNotificationsError(
            f"send exceeded notification for org_ids: {org_ids} owners: {owners} error status code {resp.status_code} content {resp.content}"
        )


def is_date_yyyy_mm_dd(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def uuid_str_to_32_chars(uuid_str):
    return uuid_str.replace("-", "")


def uuid_str_to_36_chars(uuid_str):
    return str(UUID(uuid_str))
