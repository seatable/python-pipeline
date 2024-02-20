import os
import time
import pymysql

DB_ROOT_USER = os.getenv("DB_ROOT_USER", "root")
DB_ROOT_PASSWD = os.getenv("DB_ROOT_PASSWD")
DB_USER = os.getenv("DB_USER")
DB_PASSWD = os.getenv("DB_PASSWD")
db_user = ""
db_passwd = ""
if DB_ROOT_USER and DB_ROOT_PASSWD:
    db_user = "root"
    db_passwd = DB_ROOT_PASSWD
elif DB_USER and DB_PASSWD:
    db_user = DB_USER
    db_passwd = DB_PASSWD
else:
    db_user = "root"
    db_passwd = ""

DB_HOST = os.getenv("DB_HOST", "seatable-mysql")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DATABASE_NAME = os.getenv("DATABASE_NAME", "scheduler")


def wait_for_mysql():
    while True:
        try:
            connection = pymysql.connect(
                host=DB_HOST, port=DB_PORT, user=db_user, passwd=db_passwd
            )
        except Exception as e:
            print("waiting for mysql server to be ready: %s", e)
            time.sleep(10)
            continue
        print("mysql server ready")
        connection.close()
        return


wait_for_mysql()

if db_user == "root":
    sql = 'mysql -h %s -u%s -p%s -e "CREATE DATABASE IF NOT EXISTS %s;"' % (
        DB_HOST,
        db_user,
        db_passwd,
        DATABASE_NAME,
    )
    os.system(sql)
sql = "mysql -h %s -u%s -p%s %s </opt/scheduler/database/initial_tables.sql" % (
    DB_HOST,
    db_user,
    db_passwd,
    DATABASE_NAME,
)
os.system(sql)

print("Initalization of database successful")
