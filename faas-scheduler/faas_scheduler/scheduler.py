import os
import logging
from threading import Thread, Event

import faas_scheduler.settings as settings


class FAASScheduler(Thread):

    def __init__(self):
        Thread.__init__(self)
        self._interval = settings.SCHEDULER_INTERVAL
        self._logfile = os.path.join(settings.LOG_DIR, 'faas-scheduler.log')

        self.finished = Event()

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self._interval)
            if not self.finished.is_set():
                logging.info('Starts to run tasks...')
                try:
                    print('task')
                    # manage_py = os.path.join(dtable_web_dir, 'manage.py')
                    # cmd = [
                    #     python_exec,
                    #     manage_py,
                    #     'scan_dtable_notification_rules',
                    # ]
                    # with open(self._logfile, 'a') as fp:
                    #     run(cmd, cwd=dtable_web_dir, output=fp)
                except Exception as e:
                    logging.exception(
                        'run tasks error: %s', e)

    def cancel(self):
        self.finished.set()
