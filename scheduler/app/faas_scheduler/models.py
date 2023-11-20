import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, \
    UniqueConstraint, Float, Date

from faas_scheduler import Base


class Task(Base):
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True)
    dtable_uuid = Column(String(36))
    owner = Column(String(255))
    org_id = Column(Integer)
    script_name = Column(String(255))
    context_data = Column(Text, nullable=True)
    trigger = Column(Text)
    last_trigger_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean)

    __table_args__ = (
        UniqueConstraint('dtable_uuid', 'script_name'),
    )

    def __init__(self, dtable_uuid, owner, org_id, script_name, context_data, trigger, is_active):
        self.dtable_uuid = dtable_uuid
        self.owner = owner
        self.org_id = org_id
        self.script_name = script_name
        self.context_data = context_data
        self.trigger = trigger
        self.is_active = is_active

    def to_dict(self):
        return {
            'id': self.id,
            'dtable_uuid': self.dtable_uuid,
            'owner': self.owner,
            'script_name': self.script_name,
            'context_data': json.loads(self.context_data) if self.context_data else None,
            'trigger': json.loads(self.trigger),
            'last_trigger_time': self.last_trigger_time,
            'is_active': self.is_active,
        }

class ScriptLog(Base):
    __tablename__ = 'script_log'
    id = Column(Integer, primary_key=True)
    dtable_uuid = Column(String(36))
    owner = Column(String(255))
    org_id = Column(Integer)
    script_name = Column(String(255))
    context_data = Column(Text, nullable=True)
    started_at = Column(DateTime, index=True)
    finished_at = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=True)
    return_code = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)
    operate_from  = Column(String(255))

    def __init__(self, dtable_uuid, owner, org_id, script_name, context_data, started_at, operate_from=None):
        self.dtable_uuid = dtable_uuid
        self.owner = owner
        self.org_id = org_id
        self.script_name = script_name
        self.context_data = context_data
        self.started_at = started_at
        self.operate_from = operate_from

    def to_dict(self):
        from faas_scheduler.utils import datetime_to_isoformat_timestr
        return {
            'id': self.id,
            'dtable_uuid': self.dtable_uuid,
            'owner': self.owner,
            'script_name': self.script_name,
            'context_data': json.loads(self.context_data) if self.context_data else None,
            'started_at': datetime_to_isoformat_timestr(self.started_at),
            'finished_at': self.finished_at and datetime_to_isoformat_timestr(self.finished_at),
            'success': self.success,
            'return_code': self.return_code,
            'output': self.output,
            'operate_from': self.operate_from,
        }


class DTableRunScriptStatistics(Base):
    __tablename__ = 'dtable_run_script_statistics'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dtable_uuid = Column(String(36), nullable=False, index=True)
    run_date = Column(Date, nullable=False)
    total_run_count = Column(Integer, default=0)
    total_run_time = Column(Float, default=0)
    update_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('dtable_uuid', 'run_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'dtable_uuid': self.dtable_uuid,
            'run_date': self.run_date,
            'total_run_count': self.total_run_count,
            'total_run_time': self.total_run_time,
            'update_at': self.update_at
        }


class UserRunScriptStatistics(Base):
    __tablename__ = 'user_run_script_statistics'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, index=True)
    run_date = Column(Date, nullable=False)
    total_run_count = Column(Integer, default=0)
    total_run_time = Column(Float, default=0)
    update_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('username', 'run_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'run_date': self.run_date,
            'total_run_count': self.total_run_count,
            'total_run_time': self.total_run_time,
            'update_at': self.update_at
        }


class OrgRunScriptStatistics(Base):
    __tablename__ = 'org_run_script_statistics'
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, nullable=False, index=True)
    run_date = Column(Date, nullable=False)
    total_run_count = Column(Integer, default=0)
    total_run_time = Column(Float, default=0)
    update_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('org_id', 'run_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'org_id': self.org_id,
            'run_date': self.run_date,
            'total_run_count': self.total_run_count,
            'total_run_time': self.total_run_time,
            'update_at': self.update_at
        }
