from gevent import monkey

monkey.patch_all()

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, make_response
from gevent.pywsgi import WSGIServer

from database import DBSession
from faas_scheduler.utils import (
    check_auth_token,
    get_script,
    get_run_script_statistics_by_month,
    hook_update_script,
    can_run_task,
    get_run_scripts_count_monthly,
    ping_starter,
    get_task_log,
    list_task_logs,
    uuid_str_to_32_chars,
    basic_log,
)
from scheduler import scheduler


basic_log("scheduler.log")

# defaults...
SCRIPT_WORKERS = int(os.environ.get("PYTHON_SCHEDULER_SCRIPT_WORKERS", 5))
SUB_PROCESS_TIMEOUT = int(os.environ.get("PYTHON_PROCESS_TIMEOUT", 60 * 15))
TIMEOUT_OUTPUT = (
    "The script's running time exceeded the limit and the execution was aborted."
)

app = Flask(__name__)

logger = logging.getLogger(__name__)


@app.teardown_appcontext
def shutdown_session(exception=None):
    DBSession.remove()


@app.route("/ping/", methods=["GET"])
def ping():
    if not ping_starter():
        return make_response(
            (
                "Error: Python Scheduler can not reach the Python Starter. Check PYTHON_STARTER_URL.",
                400,
            )
        )
    return make_response(("Pong", 200))


# called from dtable-web to start the python run
@app.route("/run-script/", methods=["POST"])
def scripts_api():
    if not check_auth_token(request):
        return make_response(("Forbidden: the auth token is not correct.", 403))

    logger.debug("dtable-web initialized the execution of a python script...")
    try:
        data = json.loads(request.data)
        if not isinstance(data, dict):
            return make_response(("Bad request", 400))
    except Exception:
        return make_response(("Bad request", 400))

    dtable_uuid = data.get("dtable_uuid")
    script_name = data.get("script_name")
    context_data = data.get("context_data")
    owner = data.get("owner")
    org_id = data.get("org_id")
    scripts_running_limit = data.get("scripts_running_limit", -1)
    operate_from = data.get("operate_from", "manualy")
    if not dtable_uuid or not script_name or not owner:
        return make_response(("Parameters invalid", 400))

    # main
    db_session = DBSession()
    logger.debug("create a database entry for this python run...")
    try:
        if scripts_running_limit != -1 and not can_run_task(
            owner, org_id, db_session, scripts_running_limit=scripts_running_limit
        ):
            return make_response(("The number of runs exceeds the limit"), 400)
        script_log = scheduler.add_script_log(
            uuid_str_to_32_chars(dtable_uuid),
            org_id,
            owner,
            script_name,
            context_data,
            operate_from
        )

        return make_response(({"script_id": script_log.id}, 200))
    except Exception as e:
        logger.exception(e)
        return make_response(("Internal server error", 500))
    finally:
        db_session.close()


# called from dtable-web to get the status of a specific run.
@app.route("/run-script/<script_id>/", methods=["GET"])
def script_api(script_id):
    if not check_auth_token(request):
        return make_response(("Forbidden: the auth token is not correct.", 403))

    logger.debug(
        "dtable-web asks for the status of the execution of the python script with the id %s",
        script_id,
    )
    try:
        script_id = int(script_id)
    except Exception:
        return make_response(("Bad request", 400))
    dtable_uuid = request.args.get("dtable_uuid")
    script_name = request.args.get("script_name")
    if not dtable_uuid or not script_name:
        return make_response(("Parameters invalid", 400))

    # main
    db_session = DBSession()
    try:
        script = get_script(db_session, script_id)
        if not script:
            return make_response(("Not found", 404))
        if dtable_uuid != script.dtable_uuid or script_name != script.script_name:
            return make_response(("Bad request", 400))

        if SUB_PROCESS_TIMEOUT and isinstance(SUB_PROCESS_TIMEOUT, int):
            now = datetime.now()
            duration_seconds = (now - script.started_at).seconds
            if duration_seconds > SUB_PROCESS_TIMEOUT:
                script.success = False
                script.return_code = -1
                script.finished_at = now
                script.output = TIMEOUT_OUTPUT
                db_session.commit()

        return make_response(({"script": script.to_dict()}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(("Internal server error", 500))
    finally:
        db_session.close()


# get python script statistics logs...
@app.route("/tasks/<dtable_uuid>/<script_name>/logs/", methods=["GET"])
def task_logs_api(dtable_uuid, script_name):
    if not check_auth_token(request):
        return make_response(("Forbidden", 403))

    try:
        current_page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
        order_by = request.args.get("org_by", "-id")
    except ValueError:
        current_page = 1
        per_page = 20

    if order_by.strip("-") not in ("id",):
        return make_response(("order_by invalid.", 400))

    start = per_page * (current_page - 1)
    end = start + per_page

    db_session = DBSession()
    try:
        task_logs = list_task_logs(db_session, dtable_uuid, script_name, order_by)
        count = task_logs.count()
        task_logs = task_logs[start:end]
        task_log_list = [task_log.to_dict() for task_log in task_logs]
        return make_response(
            (
                {
                    "task_logs": task_log_list,
                    "count": count,
                },
                200,
            )
        )

    except Exception as e:
        logger.exception(e)
        return make_response(("Internal server error", 500))
    finally:
        db_session.close()


# get python script statistics logs details!
@app.route("/tasks/<dtable_uuid>/<script_name>/logs/<log_id>/", methods=["GET"])
def task_log_api(dtable_uuid, script_name, log_id):
    if not check_auth_token(request):
        return make_response(("Forbidden", 403))

    db_session = DBSession()
    try:
        task_log = get_task_log(db_session, log_id)
        if uuid_str_to_32_chars(task_log.dtable_uuid) != uuid_str_to_32_chars(
            dtable_uuid
        ):
            return make_response(({"error_msg": "Script log not found"}, 404))
        if task_log.script_name != script_name:
            return make_response(({"error_msg": "Script log not found"}, 404))
        task_log_info = task_log.to_dict()

        return make_response(({"task_log": task_log_info}, 200))

    except Exception as e:
        logger.exception(e)
        return make_response(("Internal server error", 500))
    finally:
        db_session.close()


# needed for api endpoint "show account info"
@app.route("/scripts-running-count/", methods=["GET"])
def scripts_running_count():
    if not check_auth_token(request):
        return make_response(("Forbidden: the auth token is not correct.", 403))

    username = request.args.get("username")
    org_id = request.args.get("org_id")
    raw_month = request.args.get("month")
    if raw_month:
        try:
            month = datetime.strptime(raw_month, "%Y-%m").strftime("%Y-%m")
        except Exception:
            return make_response(("month invalid.", 400))
    else:
        month = None

    if not username and not org_id:
        return make_response(("username or org_id invalid.", 400))

    if org_id:
        try:
            org_id = int(org_id)
        except Exception:
            return make_response(("org_id invalid.", 400))
        if org_id == -1:
            return make_response(("org_id invalid.", 400))

    db_session = DBSession()
    try:
        count = get_run_scripts_count_monthly(username, org_id, db_session, month=month)
    except Exception as e:
        logger.error(e)
        return make_response(("Internal server error", 500))
    finally:
        db_session.close()

    return make_response(({"count": count}, 200))


# endpoint to be informed that the execution of python code is done. (from starter)
@app.route("/script-result/", methods=["POST"])
def record_script_result():
    """
    Receive result of script from python-starter
    """
    try:
        data = request.get_json()
    except Exception:
        return make_response("Bad Request.", 400)
    success = data.get("success", False)
    return_code = data.get("return_code")
    output = data.get("output")
    spend_time = data.get("spend_time")
    script_id = data.get("script_id")

    db_session = DBSession()

    # update script_log and run-time statistics
    try:
        if script_id:
            hook_update_script(
                db_session, script_id, success, return_code, output, spend_time
            )

    except Exception as e:
        logger.exception(e)
        return make_response(("Internal server error", 500))
    finally:
        db_session.close()

    return "success"


# internal function...
def get_scripts_running_statistics_by_request(api_request, target):
    raw_month = api_request.args.get("month")
    if raw_month:
        try:
            month = datetime.strptime(raw_month, "%Y-%m")
        except Exception:
            return make_response(("month invalid.", 400))
    else:
        month = None

    order_by = api_request.args.get("order_by")
    if order_by:
        if order_by.strip("-") not in ("total_run_time", "total_run_count"):
            return make_response(("order_by invalid.", 400))
        if "-" in order_by:
            order_by = order_by.strip("-") + " DESC"

    direction = api_request.args.get("direction")

    try:
        page = int(api_request.args.get("page", 1))
        per_page = int(api_request.args.get("per_page", 25))
    except Exception:
        page, per_page = 1, 25

    start, limit = (page - 1) * per_page, per_page

    db_session = DBSession()
    try:
        month, total_count, results = get_run_script_statistics_by_month(
            db_session,
            target,
            month=month,
            start=start,
            limit=limit,
            order_by=order_by,
            direction=direction,
        )
    except Exception as e:
        logger.error(e)
        logger.exception(e)
        return make_response(("Internal Server Error.", 500))
    finally:
        db_session.close()

    return make_response(
        ({"month": month, "count": total_count, "results": results}, 200)
    )


# admin statistics
@app.route("/admin/statistics/scripts-running/by-user/", methods=["GET"])
def user_run_python_statistics():
    if not check_auth_token(request):
        return make_response(("Forbidden: the auth token is not correct.", 403))

    return get_scripts_running_statistics_by_request(request, target="user")


# admin statistics
@app.route("/admin/statistics/scripts-running/by-org/", methods=["GET"])
def org_run_python_statistics():
    if not check_auth_token(request):
        return make_response(("Forbidden: the auth token is not correct.", 403))

    return get_scripts_running_statistics_by_request(request, target="org")


# admin statistics
@app.route("/admin/statistics/scripts-running/by-base/", methods=["GET"])
def base_run_python_statistics():
    if not check_auth_token(request):
        return make_response(("Forbidden: the auth token is not correct.", 403))

    return get_scripts_running_statistics_by_request(request, target="base")


if __name__ == "__main__":
    scheduler.start()
    http_server = WSGIServer(("127.0.0.1", 5055), app)
    http_server.serve_forever()
