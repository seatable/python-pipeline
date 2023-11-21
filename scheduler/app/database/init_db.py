import os
import time
import pymysql

DB_ROOT_USER = os.getenv('DB_ROOT_USER', 'root')
DB_ROOT_PASSWD = os.getenv('DB_ROOT_PASSWD', '')
DB_HOST = os.getenv('DB_HOST', 'seatable-mysql')
DB_PORT = os.getenv('DB_PORT', 3306)
DATABASE_NAME = os.getenv('DATABASE_NAME', 'scheduler')

def wait_for_mysql():
    while True:
        try:
            pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_ROOT_USER, passwd=DB_ROOT_PASSWD)
        except Exception as e:
            print ('waiting for mysql server to be ready: %s', e)
            time.sleep(10)
            continue
        print('mysql server ready')
        return


wait_for_mysql()

sql = 'mysql -h %s -p%s -e "CREATE DATABASE IF NOT EXISTS %s;"' % (DB_HOST, DB_ROOT_PASSWD, DATABASE_NAME)
os.system(sql)
sql = 'mysql -h %s -p%s %s </opt/scheduler/database/initial_tables.sql' % (DB_HOST, DB_ROOT_PASSWD, DATABASE_NAME)
os.system(sql)

print('Initalization of database successful')
