#!/usr/bin/env python3
#coding: UTF-8

"""
This script is used to run proper upgrade scripts automatically.
"""

import glob
import os
from os.path import abspath, basename, exists, dirname, join, isdir, islink
import time
import pymysql
from sqlalchemy import text
from datetime import datetime

import sys
sys.path.append('/opt/scheduler')
from database import DBSession

DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWD = os.getenv('DB_PASSWD', '')
DB_HOST = os.getenv('DB_HOST', 'seatable-mysql')
DB_PORT = os.getenv('DB_PORT', '3306')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'scheduler')
CURRENT_VERSION = os.getenv('VERSION', '2.6.0')

#SCHEDULER_VERSION_ENV = 'SCHEDULER_VERSION'
top_dir = '/opt/scheduler/'
sql_dir = top_dir + 'upgrade/'


def collect_upgrade_scripts(from_version, to_version):
    """
    Give the current installed version, calculate which upgrade scripts we need
    to run to upgrade it to the latest version.

    For example, given current version 3.0.0 and target version 2.5.0, and these
    upgrade scripts:

        2.5.0.sql
        2.7.0.sql
        2.9.0.sql
        3.0.0.sql

    We need to run 2.7.0.sql, 2.9.0.sql, and 3.0.0.sql.
    """
    scripts = []
    from_version = tuple(int(v) for v in from_version.split('.'))
    to_version = tuple(int(v) for v in to_version.split('.'))
    for fn in sorted(glob.glob(join(sql_dir, '*.*.*.sql'))):
        v = parse_upgrade_script_version(fn)
        if from_version < v and v <= to_version:
            scripts.append(fn)
    return scripts


def parse_upgrade_script_version(script):
    name = basename(script)
    version = name.rstrip('.sql')
    return tuple(int(v) for v in version.split('.'))


def run_script_and_update_version_stamp(script, new_version):
    os.system('mysql -h %(db_host)s -u%(db_user)s -p%(db_passwd)s %(database)s < %(script)s' % {
        'db_host': DB_HOST,
        'db_user': DB_USER,
        'db_passwd': DB_PASSWD,
        'database': DATABASE_NAME,
        'script': script
    })
    update_version_stamp(new_version)


def read_version_stamp():
    db_session = DBSession()
    sql = 'SELECT version FROM version_history ORDER BY update_at DESC LIMIT 1;'
    try:
        last_one = db_session.execute(text(sql)).fetchone()
        if not last_one:  # version_history exists but no records
            return '2.2.4'
        return last_one[0]
    except Exception as e:
        return None

def update_version_stamp(version):
    db_session = DBSession()
    sql = 'INSERT INTO version_history (version, update_at) VALUES ("%s", "%s");' % (CURRENT_VERSION, datetime.now())
    try:
        db_session.execute(text(sql))
        db_session.commit()
    except Exception as e:
        print(e)

def check_upgrade():
    last_version = read_version_stamp()
    if last_version == CURRENT_VERSION:
        print('No database update needed')
        return

    if last_version == None:
        update_version_stamp(CURRENT_VERSION)    
        return

    # Now we do the upgrade, if versions are different
    scripts_to_run = collect_upgrade_scripts(from_version=last_version, to_version=CURRENT_VERSION)
    for script in scripts_to_run:
        print('Running database update: {}'.format(script))
        new_version = parse_upgrade_script_version(script)
        run_script_and_update_version_stamp(script, new_version)

    update_version_stamp(CURRENT_VERSION)
    print('Database upgrade successful.')


def main():
    check_upgrade()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error:', type(e), e)
        print('Auto upgrade failed, please run the folloging command manually: scheduler.sh upgrade-sql x.x.x')
