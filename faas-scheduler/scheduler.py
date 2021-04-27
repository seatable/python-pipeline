import os
import gc
import time
import logging
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from faas_scheduler import DBSession
import faas_scheduler.settings as settings
from faas_scheduler.utils import list_tasks_to_run, run_task

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s'
)
logger = logging.getLogger(__name__)


class FAASScheduler(object):

    def __init__(self):
        self.interval = settings.SCHEDULER_INTERVAL
        self.logfile = os.path.join(settings.LOG_DIR, 'scheduler.log')
        self.executor = ThreadPoolExecutor(
            max_workers=settings.SCHEDULER_WORKERS)

    def start(self):
        while True:
            logger.info('Start run tasks...')
            db_session = DBSession()
            try:
                # main
                tasks = list_tasks_to_run(db_session)
                logger.info('Found %d tasks to run...' % len(tasks))

                all_tasks = [
                    self.executor.submit(run_task, task) for task in tasks]
                wait(all_tasks, return_when=ALL_COMPLETED)
            except Exception as e:
                logger.exception('Run tasks error: %s' % e)
            finally:
                db_session.close()

            # sleep
            logger.info('gc.collect: ' + str(gc.collect()))
            logger.info('Sleep %d...' % self.interval)
            time.sleep(self.interval)


if __name__ == '__main__':
    scheduler = FAASScheduler()
    scheduler.start()
