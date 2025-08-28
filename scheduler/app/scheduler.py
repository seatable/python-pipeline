import json
import logging
import os
import time
from threading import Lock, Thread

from database import DBSession
from faas_scheduler.models import ScriptLog
from faas_scheduler.utils import (
    add_script,
    run_script,
    get_script_file,
    hook_update_script
)

logger = logging.getLogger(__name__)


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
            run_limit_per_team = os.environ.get('RUN_LIMIT_PER_TEAM', 0)
        except:
            run_limit_per_team = 0
        try:
            run_limit_per_base = os.environ.get('RUN_LIMIT_PER_BASE', 0)
        except:
            run_limit_per_base = 0
        try:
            run_limit_per_script = os.environ.get('RUN_LIMIT_PER_SCRIPT', 0)
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
                    break
                index += 1

            return return_task

    def script_done_callback(self, script_log: ScriptLog):
        with self.lock:
            if script_log.org_id != -1:
                running_team_key = f'{script_log.org_id}'
            else:
                running_team_key = f'{script_log.owner}'
            running_base_key = f'{running_team_key}_{script_log.dtable_uuid}'
            running_script_key = f'{running_base_key}_{script_log.script_name}'
            if running_team_key in self.running_count:
                self.running_count[running_team_key] -= 1
            if running_base_key in self.running_count:
                self.running_count[running_base_key] -= 1
            if running_script_key in self.running_count:
                self.running_count[running_script_key] -= 1


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
            try:
                script_file_info = get_script_file(script_log.dtable_uuid, script_log.script_name)
                run_script(
                    script_log.script_id,
                    script_log.dtable_uuid,
                    script_log.script_name,
                    script_file_info['script_url'],
                    script_file_info['temp_api_token'],
                    json.loads(script_log.context_data)
                )
            except Exception as e:
                logger.exception(f'run script: {script_log} error {e}')

    def script_done_callback(
            self,
            script_id,
            success,
            return_code,
            output,
            spend_time
        ):
        script_log = self.script_queue.script_logs_dict.pop(script_id)
        hook_update_script(
            DBSession(),
            script_id,
            success,
            return_code,
            output,
            spend_time
        )
        if not script_log:  # not counted in memory, only update db record
            return

    def load_pending_script_logs(self):
        """load pending script logs, should be called only when server start
        """
        script_logs = DBSession.query(ScriptLog).filter_by(state=ScriptLog.PENDING).order_by(ScriptLog.id)
        for script_log in script_logs:
            self.script_queue.add_script_log(script_log)

    def start(self):
        self.load_pending_script_logs()
        Thread(target=self.schedule, daemon=True).start()


scheduler = Scheduelr()
