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


SCHEDULER_VERSION_ENV = 'SCHEDULER_VERSION'
top_dir = '/opt/scheduler/'
conf_dir = top_dir + 'conf/'
sql_dir = top_dir + 'upgrade/'
version_stamp_file = conf_dir + 'current_version'

# mysql user and passwd
DB_HOST = os.getenv('DB_HOST', 'db')
DB_ROOT_PASSWD = os.getenv('DB_ROOT_PASSWD', '')
DB_USER = os.getenv('DB_USER', '')
DB_USER_PASSWD = os.getenv('DB_USER_PASSWD', '')
if DB_USER and DB_USER_PASSWD:
    db_user = DB_USER
    db_passwd = DB_USER_PASSWD
else:
    db_user = 'root'
    db_passwd = DB_ROOT_PASSWD


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
    for fn in sorted(glob.glob(join(sql_dir, '*.*.*.sql'))):
        v = parse_upgrade_script_version(fn)
        if from_version < v and v <= to_version:
            scripts.append(fn)
    return scripts


def parse_upgrade_script_version(script):
    name = basename(script)
    version = name.rstrip('.sql')
    return version


def run_script_and_update_version_stamp(script, new_version):
    os.system('mysql -h %(db_host)s -u%(db_user)s -p%(db_passwd)s faas_scheduler <%(script)s' % {
        'db_host': DB_HOST,
        'db_user': db_user,
        'db_passwd': db_passwd,
        'script': script
    })
    update_version_stamp(new_version)


def read_version_stamp(fn=version_stamp_file):
    if not exists(fn):
        with open(fn, 'w') as fp:
            fp.write('2.1.0\n')  # default 2.1.0
    with open(fn, 'r') as fp:
        return fp.read().strip()


def update_version_stamp(version, fn=version_stamp_file):
    with open(fn, 'w') as fp:
        fp.write(version + '\n')


def wait_for_mysql():
    while True:
        try:
            pymysql.connect(host=DB_HOST, port=3306, user=db_user, passwd=db_passwd)
        except Exception as e:
            print ('waiting for mysql server to be ready: %s', e)
            time.sleep(2)
            continue
        print('mysql server is ready')
        return


def check_upgrade():
    last_version = read_version_stamp()
    current_version = os.environ[SCHEDULER_VERSION_ENV]
    if last_version == current_version:
        return

    # Now we do the upgrade
    scripts_to_run = collect_upgrade_scripts(from_version=last_version, to_version=current_version)
    for script in scripts_to_run:
        print('Running scripts {}'.format(script))
        new_version = parse_upgrade_script_version(script)
        run_script_and_update_version_stamp(script, new_version)

    update_version_stamp(current_version)
    print('Auto upgrade successful.')


def main():
    wait_for_mysql()
    check_upgrade()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error:', type(e), e)
        print('Auto upgrade failed, please run < scheduler.sh upgrade-sql x.x.x > manually.')
