import os
import time
import pymysql

DB_HOST = os.getenv('DB_HOST', 'db')
DB_ROOT_PASSWD = os.getenv('DB_ROOT_PASSWD', '')


def wait_for_mysql():
    while True:
        try:
            pymysql.connect(host=DB_HOST, port=3306, user='root', passwd=DB_ROOT_PASSWD)
        except Exception as e:
            print ('waiting for mysql server to be ready: %s', e)
            time.sleep(10)
            continue
        print('mysql server ready')
        return


wait_for_mysql()

os.system('mysql -h $DB_HOST -p$DB_ROOT_PASSWD -e "create database faas_scheduler charset utf8";')
os.system('mysql -h $DB_HOST -p$DB_ROOT_PASSWD faas_scheduler </opt/scheduler/database/mysql.sql')

print('Initalization of database success')
