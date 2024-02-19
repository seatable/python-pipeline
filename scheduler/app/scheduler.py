import os
import gc
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from threading import Thread

from database import DBSession
from faas_scheduler.utils import (
    check_and_set_tasks_timeout,
    delete_log_after_days,
    delete_statistics_after_days,
)

LOG_LEVEL = os.environ.get("PYTHON_SCHEDULER_LOG_LEVEL", "INFO")
SUB_PROCESS_TIMEOUT = int(
    os.environ.get("PYTHON_PROCESS_TIMEOUT", 60 * 15)
)  # 15 minutes

logging.basicConfig(
    stream=sys.stdout,
    format="[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s",
    level=LOG_LEVEL,
)
logger = logging.getLogger(__name__)


class FAASTaskTimeoutSetter(Thread):

    def __init__(self):
        super(FAASTaskTimeoutSetter, self).__init__()
        self.interval = 60 * 30  # every half an hour

    def run(self):
        if SUB_PROCESS_TIMEOUT and isinstance(SUB_PROCESS_TIMEOUT, int):
            while True:
                logger.info("Start automatic cleanup ...")
                db_session = DBSession()
                try:
                    check_and_set_tasks_timeout(db_session)
                except Exception as e:
                    logger.exception("task cleaner error: %s" % e)
                finally:
                    db_session.close()

                # python garbage collection
                logger.info("gc.collect: " + str(gc.collect()))

                # remove old script_logs and statistics
                delete_log_after_days(db_session)
                delete_statistics_after_days(db_session)

                # sleep
                logger.info("Sleep for %d seconds ..." % self.interval)
                time.sleep(self.interval)


if __name__ == "__main__":
    task_timeout_setter = FAASTaskTimeoutSetter()
    task_timeout_setter.start()
