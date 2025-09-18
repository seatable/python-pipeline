import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock, Thread

from database import DBSession
from faas_scheduler.models import ScriptLog
from faas_scheduler.utils import (
    add_script,
    delete_log_after_days,
    delete_statistics_after_days,
    run_script,
    get_script_file,
    hook_update_script,
    check_and_set_tasks_timeout,
)

logger = logging.getLogger(__name__)
SUB_PROCESS_TIMEOUT = int(os.environ.get("PYTHON_PROCESS_TIMEOUT", 60 * 15))


class Scheduelr:

    def __init__(self):
        self.executor = ThreadPoolExecutor()

    def add(self, db_session, dtable_uuid, org_id, owner, script_name, context_data, operate_from):
        script_log = add_script(
            db_session,
            dtable_uuid,
            owner,
            org_id,
            script_name,
            context_data,
            operate_from,
        )
        script_file_info = get_script_file(
            script_log.dtable_uuid, script_log.script_name
        )
        self.executor.submit(
            run_script,
            script_log.id,
            dtable_uuid,
            script_name,
            script_file_info["script_url"],
            script_file_info["temp_api_token"],
            context_data,
        )
        return script_log

    def script_done_callback(
        self, db_session, script_id, success, return_code, output, started_at, spend_time
    ):
        hook_update_script(
            db_session, script_id, success, return_code, output, started_at, spend_time
        )

    def statistic_cleaner(self):
        while True:
            db_session = DBSession()
            try:
                delete_log_after_days(db_session)
                delete_statistics_after_days(db_session)
            except Exception as e:
                logger.exception(e)
            finally:
                db_session.close()
            time.sleep(24 * 60 * 60)

    def start(self):
        Thread(target=self.statistic_cleaner, daemon=True).start()


scheduler = Scheduelr()
