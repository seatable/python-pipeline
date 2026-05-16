import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from queue import Queue
from threading import Thread, Lock

from database import DBSession
from faas_scheduler.constants import SCRIPTS_KEY
from faas_scheduler.models import ScriptLog
from faas_scheduler.redis_client import RedisClient
from faas_scheduler.utils import (
    get_script_content,
    update_script,
    delete_log_after_days,
    delete_statistics_after_days,
    update_running_scripts_timeout,
    send_exceeded_notifications,
)

logger = logging.getLogger(__name__)


SEATABLE_SERVER_URL = os.environ.get("SEATABLE_SERVER_URL")
REDIS_SCRIPTS_QUEUE_MAX_SIZE = int(os.environ.get("REDIS_SCRIPTS_QUEUE_MAX_SIZE", "1"))


class Scheduler:

    def __init__(self):
        self.window_secs = int(os.environ.get("PYTHON_SCHEDULER_WINDOW_SECS", "300"))
        self.rate_limit_percent = float(
            os.environ.get("PYTHON_SCHEDULER_RATE_LIMIT_PERCENT", "0.25")
        )
        self.python_starter_total_thread_count = int(
            os.environ.get("PYTHON_STARTER_TOTAL_THREAD_COUNT", 10)
        )

        self.queue = Queue()

        self.start_time = None
        self.exceed_entities_since_start_time = {"org_ids": [], "owners": []}
        self.usage_statistics = defaultdict(
            dict
        )  # team_or_user -> {start_time: float, spend_time: float}

        self.lock = Lock()

        self.redis_client = RedisClient()

    # -------- public apis --------
    def add_script(self, script_log_info: dict):
        self.queue.put(script_log_info)

    def on_script_done(self, script_log_info: dict, spend_time: float):
        with self.lock:
            team_or_user = self.get_team_or_user(script_log_info)
            usage_info = self.usage_statistics.get(team_or_user)
            if not usage_info:
                self.usage_statistics[team_or_user] = {
                    "start_time": self.start_time,
                    "spend_time": spend_time,
                }
            else:
                if usage_info["start_time"] < self.start_time:
                    self.usage_statistics[team_or_user] = {
                        "start_time": self.start_time,
                        "spend_time": spend_time,
                    }
                else:
                    usage_info["spend_time"] += spend_time

    def start(self):
        self.load_pending_script_logs()
        Thread(target=self.schedule, daemon=True).start()
        Thread(target=self.loop_clean_up, daemon=True).start()
        Thread(target=self.loop_clean_db_records, daemon=True).start()
        Thread(target=self.loop_update_running_scripts_timeout, daemon=True).start()

    # -------- private methods --------
    def get_team_or_user(self, script_log_info: dict):
        if script_log_info["org_id"] == -1:
            return script_log_info["owner"]
        else:
            return script_log_info["org_id"]

    def clean_up(self):
        with self.lock:
            to_be_cleaned_team_or_user = [
                team_or_user
                for team_or_user, info in self.usage_statistics.items()
                if info["start_time"] < self.start_time
            ]
            for team_or_user in to_be_cleaned_team_or_user:
                self.usage_statistics.pop(team_or_user)

    def get_usage_by_team_or_user(self, team_or_user):
        with self.lock:
            usage_info = self.usage_statistics.get(team_or_user)
            if not usage_info:
                return 0.0
            else:
                if usage_info["start_time"] < self.start_time:
                    self.usage_statistics.pop(team_or_user, None)
                    return 0.0
                else:
                    return usage_info["spend_time"]

    def run_script(self, script_log_info: dict):
        now = time.time()

        db_session = DBSession()
        try:
            db_session.query(ScriptLog).filter(
                ScriptLog.id == script_log_info["id"]
            ).update({ScriptLog.state: ScriptLog.RUNNING})
            db_session.commit()
            script_content_info = get_script_content(
                script_log_info["dtable_uuid"], script_log_info["script_name"]
            )
            self.redis_client.lpush(
                SCRIPTS_KEY,
                json.dumps(
                    {
                        "script_id": script_log_info["id"],
                        "script_content": script_content_info["script_content"],
                        "dtable_uuid": script_log_info["dtable_uuid"],
                        "env": {
                            "dtable_web_url": SEATABLE_SERVER_URL.rstrip("/"),
                            "api_token": script_content_info["temp_api_token"],
                        },
                        "context_data": script_log_info["context_data"],
                    }
                ),
            )
            logger.info(
                "dispatched script id %s org_id %s owner %s dtable_uuid %s script_name %s",
                script_log_info["id"],
                script_log_info["org_id"],
                script_log_info["owner"],
                script_log_info["dtable_uuid"],
                script_log_info["script_name"],
            )
        except Exception as e:
            logger.exception(
                "dispatched script id %s org_id %s owner %s dtable_uuid %s script_name %s error %s",
                script_log_info["id"],
                script_log_info["org_id"],
                script_log_info["owner"],
                script_log_info["dtable_uuid"],
                script_log_info["script_name"],
                e,
            )
            try:
                script_log = (
                    db_session.query(ScriptLog)
                    .filter(ScriptLog.id == script_log_info["id"])
                    .first()
                )
                update_script(
                    db_session,
                    script_log,
                    False,
                    -1,
                    "Failed",
                    datetime.fromtimestamp(now),
                    datetime.fromtimestamp(now),
                )
            except Exception as ee:
                logger.exception(
                    "update script id %s org_id %s owner %s dtable_uuid %s script_name %s finished error %s",
                    script_log_info["id"],
                    script_log_info["org_id"],
                    script_log_info["owner"],
                    script_log_info["dtable_uuid"],
                    script_log_info["script_name"],
                    ee,
                )
            finally:
                db_session.close()
            self.on_script_done(script_log_info, 0)

    def load_pending_script_logs(self):
        db_session = DBSession()
        try:
            script_logs = list(
                db_session.query(ScriptLog)
                .filter_by(state=ScriptLog.PENDING)
                .order_by(ScriptLog.id)
            )
            logger.info("load %s pending scripts", len(script_logs))
            for script_log in script_logs:
                self.add_script(script_log.to_dict())
        except Exception as e:
            logger.exception("load pending script logs error %s", e)
        finally:
            db_session.close()

    # -------- scheduler loop --------
    def schedule(self):
        logger.info(
            "Start scheduler loop, window_secs: %s rate_limit_percent: %s%%",
            self.window_secs,
            self.rate_limit_percent * 100,
        )
        while True:
            if self.redis_client.llen(SCRIPTS_KEY) >= REDIS_SCRIPTS_QUEUE_MAX_SIZE:
                time.sleep(0.1)
                continue

            now = time.time()
            if not self.start_time or self.start_time + self.window_secs < now:
                self.start_time = now
                self.exceed_entities_since_start_time = {"org_ids": [], "owners": []}

            script_log_info = self.queue.get()
            team_or_user = self.get_team_or_user(script_log_info)

            usage = self.get_usage_by_team_or_user(team_or_user)

            logger.info(
                "script %s org_id %s owner %s dtable_uuid %s script_name %s used time %s percent %s%%",
                script_log_info["id"],
                script_log_info["org_id"],
                script_log_info["owner"],
                script_log_info["dtable_uuid"],
                script_log_info["script_name"],
                usage,
                usage
                / (self.window_secs * self.python_starter_total_thread_count)
                * 100,
            )

            if (
                usage / (self.window_secs * self.python_starter_total_thread_count)
                < self.rate_limit_percent
            ):
                self.run_script(script_log_info)
            else:
                db_session = DBSession()
                try:
                    script_log = (
                        db_session.query(ScriptLog)
                        .filter(ScriptLog.id == script_log_info["id"])
                        .first()
                    )
                    update_script(
                        db_session,
                        script_log,
                        False,
                        -1,
                        "Running scripts too frequently in a short period of time",
                        datetime.fromtimestamp(now),
                        datetime.fromtimestamp(now),
                    )
                except Exception as e:
                    logger.exception(
                        "script %s org_id %s owner %s dtable_uuid %s script_name %s update result error %s",
                        script_log_info["id"],
                        script_log_info["org_id"],
                        script_log_info["owner"],
                        script_log_info["dtable_uuid"],
                        script_log_info["script_name"],
                        e,
                    )
                finally:
                    db_session.close()
                self.on_script_done(script_log_info, 0)

                # send exceeded notifications and record
                try:
                    if script_log_info["org_id"] != -1:
                        if (
                            script_log_info["org_id"]
                            not in self.exceed_entities_since_start_time["org_ids"]
                        ):
                            # send notification
                            send_exceeded_notifications(
                                [script_log_info["org_id"]], None
                            )
                            self.exceed_entities_since_start_time["org_ids"].append(
                                script_log_info["org_id"]
                            )
                    else:
                        if "@seafile_group" not in script_log_info["owner"]:
                            if (
                                script_log_info["owner"]
                                not in self.exceed_entities_since_start_time["owners"]
                            ):
                                # send notification
                                send_exceeded_notifications(
                                    None, [script_log_info["owner"]]
                                )
                                self.exceed_entities_since_start_time["owners"].append(
                                    script_log_info["owner"]
                                )
                except Exception as e:
                    logger.exception(e)

    # -------- clean usage_statistics --------
    def loop_clean_up(self):
        while True:
            time.sleep(5 * 60)
            self.clean_up()

    # -------- clean db records loop --------
    def loop_clean_db_records(self):
        while True:
            time.sleep(24 * 60 * 60)
            db_session = DBSession()
            try:
                delete_log_after_days(db_session)
                delete_statistics_after_days(db_session)
            except Exception as e:
                logger.exception("clean db records error %s", e)
            finally:
                db_session.close()

    # -------- update state loop --------
    def loop_update_running_scripts_timeout(self):
        while True:
            time.sleep(15 * 60)
            db_session = DBSession()
            try:
                update_running_scripts_timeout(db_session)
            except Exception as e:
                logger.exception("update running scripts timeout error %s", e)
            finally:
                db_session.close()
