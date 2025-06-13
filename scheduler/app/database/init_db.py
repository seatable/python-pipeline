import os
import shlex
import time
import pymysql

DB_ROOT_USER = os.getenv("DB_ROOT_USER", "root")
DB_ROOT_PASSWD = os.getenv("DB_ROOT_PASSWD")
DB_USER = os.getenv("DB_USER")
DB_PASSWD = os.getenv("DB_PASSWD")
db_user = ""
db_passwd = ""
if DB_USER:
    db_user = DB_USER
    db_passwd = DB_PASSWD
else:
    db_user = "root"
    db_passwd = DB_ROOT_PASSWD

DB_HOST = os.getenv("DB_HOST", "seatable-mysql")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
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


def check_and_create_mysql_user():
    connection = pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_ROOT_USER, passwd=DB_ROOT_PASSWD
    )

    try:
        with connection.cursor() as cursor:
            if db_user != "root":
                query_user_exists = f"SELECT EXISTS(SELECT 1 FROM mysql.user WHERE User='{db_user}' AND Host='%') AS user_exists;"
                cursor.execute(query_user_exists)
                result = cursor.fetchone()
                user_exists = result[0] == 1
                if not user_exists:
                    create_user_sql = (
                        f"CREATE USER '{db_user}'@'%' IDENTIFIED BY '{db_passwd}';"
                    )
                    cursor.execute(create_user_sql)
                    print(f"Create user '{db_user}'@'%' sucessfully.")

                grant_privileges_sql = (
                    f"GRANT ALL PRIVILEGES ON {DATABASE_NAME}.* TO '{db_user}'@'%';"
                )
                for stmt in grant_privileges_sql.split(";"):
                    if stmt.strip():
                        cursor.execute(stmt)
                print(f"Granted user '{db_user}'@'%' privileges sucessfully.")

                cursor.execute("FLUSH PRIVILEGES;")
    finally:
        connection.close()


wait_for_mysql()

sql = 'mysql -h %s -u%s -p%s -e "CREATE DATABASE IF NOT EXISTS %s;"' % (
    shlex.quote(DB_HOST),
    shlex.quote(DB_ROOT_USER),
    shlex.quote(DB_ROOT_PASSWD),
    DATABASE_NAME,
)
os.system(sql)

check_and_create_mysql_user()

sql = "mysql -h %s -u%s -p%s %s </opt/scheduler/database/initial_tables.sql" % (
    shlex.quote(DB_HOST),
    shlex.quote(DB_ROOT_USER),
    shlex.quote(DB_ROOT_PASSWD),
    DATABASE_NAME,
)
os.system(sql)

print("Initalization of database successful")
