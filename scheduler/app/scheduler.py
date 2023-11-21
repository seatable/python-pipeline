import os
import gc
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from threading import Thread

from database import DBSession
from faas_scheduler.utils import check_and_set_tasks_timeout, delete_log_after_days

LOG_LEVEL = os.environ.get('PYTHON_SCHEDULER_LOG_LEVEL', 'INFO')
SUB_PROCESS_TIMEOUT = os.environ.get('PYTHON_PROCESS_TIMEOUT', 900) # 60*15 = 900 or 15 minutes

logging.basicConfig(stream=sys.stdout, format="[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s", level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# defaults...
#SCRIPT_WORKERS = 5
#SCHEDULER_INTERVAL = 3600
#SCHEDULER_WORKERS = 3
#LOG_DIR = '/opt/scheduler/logs/'

## deprecated...
#class FAASScheduler(Thread):
#
#    def __init__(self):
#        super(FAASScheduler, self).__init__()
#        self.interval = SCHEDULER_INTERVAL
#        self.logfile = os.path.join(LOG_DIR, 'scheduler.log')
#        self.executor = ThreadPoolExecutor(
#            max_workers=SCHEDULER_WORKERS)
#
#    def run(self):
#        while True:
#            logger.info('Start run tasks...')
#            db_session = DBSession()
#            try:
#                # main
#                tasks = list_tasks_to_run(db_session)
#                logger.info('Found %d tasks to run...' % len(tasks))
#
#                all_tasks = [
#                    self.executor.submit(run_task, task) for task in tasks]
#                wait(all_tasks, return_when=ALL_COMPLETED)
#            except Exception as e:
#                logger.exception('Run tasks error: %s' % e)
#            finally:
#                db_session.close()
#
#            # sleep
#            logger.info('gc.collect: ' + str(gc.collect()))
#            logger.info('Sleep %d...' % self.interval)
#            time.sleep(self.interval)

## deprecated...
#class FAASTaskCleaner(Thread):
#
#    def __init__(self):
#        super(FAASTaskCleaner, self).__init__()
#        self.interval = 60 * 60 * 24
#        self.logfile = os.path.join(LOG_DIR, 'scheduler.log')
#
#    def run(self):
#        while True:
#            logger.info('Start task cleaner...')
#            db_session = DBSession()
#            try:
#                remove_invalid_tasks(db_session)
#            except Exception as e:
#                logger.exception('task cleaner error: %s' % e)
#            finally:
#                db_session.close()
#
#            # sleep
#            logger.info('gc.collect: ' + str(gc.collect()))
#            logger.info('Sleep %d...' % self.interval)
#            time.sleep(self.interval)


class FAASTaskTimeoutSetter(Thread):

    def __init__(self):
        super(FAASTaskTimeoutSetter, self).__init__()
        self.interval = 60 * 30 # every half an hour

    def run(self):
        if SUB_PROCESS_TIMEOUT and isinstance(SUB_PROCESS_TIMEOUT, int):
            while True:
                logger.info('Start automatic cleanup ...')
                db_session = DBSession()
                try:
                    check_and_set_tasks_timeout(db_session)
                except Exception as e:
                    logger.exception('task cleaner error: %s' % e)
                finally:
                    db_session.close()

                # python garbage collection
                logger.info('gc.collect: ' + str(gc.collect()))

                # remove old script_logs 
                delete_log_after_days(db_session)

                # sleep
                logger.info('Sleep %d... seconds' % self.interval)
                time.sleep(self.interval)


if __name__ == '__main__':
    task_timeout_setter = FAASTaskTimeoutSetter()
    task_timeout_setter.start()
