import json
import logging
import os
import time
from datetime import datetime
from threading import Lock, Thread

from database import DBSession
from faas_scheduler.models import ScriptLog
from faas_scheduler.utils import (
    add_script,
    delete_log_after_days,
    delete_statistics_after_days,
    run_script,
    get_script_file,
    hook_update_script
)

logger = logging.getLogger(__name__)
SUB_PROCESS_TIMEOUT = int(os.environ.get("PYTHON_PROCESS_TIMEOUT", 60 * 15))
TIMEOUT_OUTPUT = "Script running for too long time!"


class ScriptQueue:

    def __init__(self):
        self.q = []  # a list of ScriptLog
        self.script_logs_dict = {}  # a dict of {id: ScriptLog}
        self.lock = Lock()
        self.running_count = {}
        # a dict of 
        # {
        #     "<team>": 0,
        #     "<team>_<dtable_uuid>": 0,
        #     "<team>_<dtable_uuid>_<script_name>": 0
        # }
        try:
            run_limit_per_team = int(os.environ.get('RUN_LIMIT_PER_TEAM', 0))
        except:
            run_limit_per_team = 0
        try:
            run_limit_per_base = int(os.environ.get('RUN_LIMIT_PER_BASE', 0))
        except:
            run_limit_per_base = 0
        try:
            run_limit_per_script = int(os.environ.get('RUN_LIMIT_PER_SCRIPT', 0))
        except:
            run_limit_per_script = 0
        self.config = {
            'run_limit_per_team': run_limit_per_team,
            'run_limit_per_base': run_limit_per_base,
            'run_limit_per_script': run_limit_per_script
        }

    def can_run_script(self, script_log: ScriptLog):
        if script_log.org_id != -1:
            running_team_key = f'{script_log.org_id}'
        else:
            running_team_key = f'{script_log.owner}'
        running_base_key = f'{running_team_key}_{script_log.dtable_uuid}'
        running_script_key = f'{running_base_key}_{script_log.script_name}'

        if self.config['run_limit_per_team'] > 0 and self.config['run_limit_per_team'] <= self.running_count.get(running_team_key, 0):
            return False
        if self.config['run_limit_per_base'] > 0 and self.config['run_limit_per_base'] <= self.running_count.get(running_base_key, 0):
            return False
        if self.config['run_limit_per_script'] > 0 and self.config['run_limit_per_script'] <= self.running_count.get(running_script_key, 0):
            return False

        return True

    def add_script_log(self, script_log: ScriptLog):
        with self.lock:
            self.q.append(script_log)
            self.script_logs_dict[script_log.id] = script_log
            self.inspect_queue_and_running(pre_msg=f'add script {script_log.get_info()} to queue')

    def get(self):
        """get the first valid task from self.q

        Return: an instance of ScriptTask or None
        """
        with self.lock:
            return_task = None

            index = 0
            while index < len(self.q):
                script_log = self.q[index]
                if self.can_run_script(script_log):
                    return_task = script_log
                    self.q.pop(index)
                    self.increase_running(script_log)
                    self.inspect_queue_and_running(pre_msg=f'get script {script_log.get_info()} from queue')
                    break
                index += 1

            return return_task

    def increase_running(self, script_log):
        if script_log.org_id != -1:
            running_team_key = f'{script_log.org_id}'
        else:
            running_team_key = f'{script_log.owner}'
        running_base_key = f'{running_team_key}_{script_log.dtable_uuid}'
        running_script_key = f'{running_base_key}_{script_log.script_name}'
        self.running_count[running_team_key] = self.running_count[running_team_key] + 1 if self.running_count.get(running_team_key) else 1
        self.running_count[running_base_key] = self.running_count[running_base_key] + 1 if self.running_count.get(running_base_key) else 1
        self.running_count[running_script_key] = self.running_count[running_script_key] + 1 if self.running_count.get(running_script_key) else 1

    def decrease_running(self, script_log):
        if script_log.org_id != -1:
            running_team_key = f'{script_log.org_id}'
        else:
            running_team_key = f'{script_log.owner}'
        running_base_key = f'{running_team_key}_{script_log.dtable_uuid}'
        running_script_key = f'{running_base_key}_{script_log.script_name}'

        if running_team_key in self.running_count:
            self.running_count[running_team_key] -= 1
        if not self.running_count.get(running_team_key):
            self.running_count.pop(running_team_key, None)

        if running_base_key in self.running_count:
            self.running_count[running_base_key] -= 1
        if not self.running_count.get(running_base_key):
            self.running_count.pop(running_base_key, None)

        if running_script_key in self.running_count:
            self.running_count[running_script_key] -= 1
        if not self.running_count.get(running_script_key):
            self.running_count.pop(running_script_key, None)

    def script_done_callback(self, script_log: ScriptLog):
        with self.lock:
            self.script_logs_dict.pop(script_log.id, None)
            self.decrease_running(script_log)
            self.inspect_queue_and_running(pre_msg=f'script {script_log.get_info()} run done')

    def inspect_queue_and_running(self, pre_msg=None):
        if logger.root.level != logging.DEBUG:
            return
        lines = ['\n']
        if pre_msg:
            lines.append(pre_msg)
        lines.append(f"{'>' * 10} running {'>' * 10}")
        for key, value in self.running_count.items():
            lines.append(f'{key}: {value}')
        lines.append(f"{'<' * 10} running {'<' * 10}")

        lines.append(f"{'>' * 10} queue {'>' * 10}")
        for script_log in self.q:
            lines.append(f"org_id: {script_log.org_id} owner: {script_log.owner} dtable_uuid: {script_log.dtable_uuid} script_name: {script_log.script_name}")
        lines.append(f"{'<' * 10} queue {'<' * 10}")
        logger.debug('\n'.join(lines))

    def get_script_log_by_id(self, script_id):
        return self.script_logs_dict.get(script_id)

    def get_timeout_scripts(self):
        script_logs = []
        now_time = datetime.now()
        with self.lock:
            for index in range(len(self.q) - 1, -1, -1):
                script_log = self.q[index]
                if (now_time - script_log.started_at).seconds >= SUB_PROCESS_TIMEOUT:
                    script_logs.append(self.q.pop(index))
                    self.script_logs_dict.pop(script_log.id, None)
        return script_logs


class Scheduelr:

    def __init__(self):
        self.script_queue = ScriptQueue()

    def add_script_log(
            self,
            dtable_uuid,
            org_id,
            owner,
            script_name,
            context_data,
            operate_from
        ):
        script_log = add_script(
            DBSession(),
            dtable_uuid,
            owner,
            org_id,
            script_name,
            context_data,
            operate_from
        )
        self.script_queue.add_script_log(script_log)
        return script_log

    def schedule(self):
        while True:
            script_log = self.script_queue.get()
            if not script_log:
                time.sleep(0.5)
                continue
            db_session = DBSession()
            try:
                db_session.query(ScriptLog).filter(ScriptLog.id==script_log.id).update(
                    {ScriptLog.state: ScriptLog.RUNNING},
                    synchronize_session=False
                )
                db_session.commit()
                script_file_info = get_script_file(script_log.dtable_uuid, script_log.script_name)
                run_script(
                    script_log.id,
                    script_log.dtable_uuid,
                    script_log.script_name,
                    script_file_info['script_url'],
                    script_file_info['temp_api_token'],
                    json.loads(script_log.context_data)
                )
            except Exception as e:
                logger.exception(f'run script: {script_log} error {e}')
            finally:
                DBSession.remove()

    def script_done_callback(
            self,
            script_id,
            success,
            return_code,
            output,
            spend_time
        ):
        hook_update_script(
            DBSession(),
            script_id,
            success,
            return_code,
            output,
            spend_time
        )
        script_log = self.script_queue.get_script_log_by_id(script_id)
        if not script_log:  # not counted in memory, only update db record
            return
        self.script_queue.script_done_callback(script_log)

    def load_pending_script_logs(self):
        """load pending script logs, should be called only when server start
        """
        script_logs = DBSession.query(ScriptLog).filter_by(state=ScriptLog.PENDING).order_by(ScriptLog.id)
        for script_log in script_logs:
            self.script_queue.add_script_log(script_log)

    def timeout_setter(self):
        while True:
            db_session = DBSession()
            now_time = datetime.now()
            try:
                script_logs = self.script_queue.get_timeout_scripts()
                if script_logs:
                    db_session.query(ScriptLog).filter(ScriptLog.id.in_([script_log.id for script_log in script_logs])).update(
                        {
                            ScriptLog.state: ScriptLog.FINISHED,
                            ScriptLog.finished_at: now_time,
                            ScriptLog.success: False,
                            ScriptLog.output: TIMEOUT_OUTPUT,
                            ScriptLog.return_code: -1
                        },
                        synchronize_session=False
                    )
            except Exception as e:
                logger.exception(e)
            finally:
                DBSession.remove()
            time.sleep(60)

    def statistic_cleaner(self):
        while True:
            db_session = DBSession()
            try:
                delete_log_after_days(db_session)
                delete_statistics_after_days(db_session)
            except Exception as e:
                logger.exception(e)
            finally:
                DBSession.remove()
            time.sleep(24 * 60 * 60)

    def start(self):
        self.load_pending_script_logs()
        Thread(target=self.schedule, daemon=True).start()
        Thread(target=self.statistic_cleaner, daemon=True).start()
        Thread(target=self.timeout_setter, daemon=True).start()


scheduler = Scheduelr()
