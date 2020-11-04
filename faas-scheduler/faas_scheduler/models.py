import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, \
    UniqueConstraint

from faas_scheduler import Base


class Task(Base):
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True)
    repo_id = Column(String(36))
    dtable_uuid = Column(String(36))
    script_name = Column(String(255))
    context_data = Column(Text, nullable=True)
    trigger = Column(Text)
    last_trigger_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean)

    __table_args__ = (
        UniqueConstraint('dtable_uuid', 'script_name'),
    )

    def __init__(self, repo_id, dtable_uuid, script_name, context_data, trigger, is_active):
        self.repo_id = repo_id
        self.dtable_uuid = dtable_uuid
        self.script_name = script_name
        self.context_data = context_data
        self.trigger = trigger
        self.is_active = is_active

    def to_dict(self):
        return {
            'id': self.id,
            'dtable_uuid': self.dtable_uuid,
            'script_name': self.script_name,
            'context_data': json.loads(self.context_data) if self.context_data else None,
            'trigger': json.loads(self.trigger),
            'last_trigger_time': self.last_trigger_time,
            'is_active': self.is_active,
        }


class TaskLog(Base):
    __tablename__ = 'task_log'
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    started_at = Column(DateTime)
    finished_at = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=True)
    return_code = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)

    def __init__(self, task_id, started_at):
        self.task_id = task_id
        self.started_at = started_at

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'started_at': self.started_at,
            'finished_at': self.finished_at,
            'success': self.success,
            'return_code': self.return_code,
        }
