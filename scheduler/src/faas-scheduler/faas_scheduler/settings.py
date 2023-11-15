import os
import sys


# mysql
MYSQL_USER = ''
MYSQL_PASSWORD = ''
MYSQL_HOST = ''
MYSQL_PORT = '3306'
DATABASE_NAME = ''

#
SCRIPT_WORKERS = 5

#
SCHEDULER_INTERVAL = 3600
SCHEDULER_WORKERS = 3

#
SEATABLE_SERVER_URL = ''
PYTHON_STARTER_URL = ''
PYTHON_SCHEDULER_AUTH_TOKEN = ''

#
CONF_DIR = '/opt/seatable-faas-scheduler/conf/'
LOG_DIR = '/opt/seatable-faas-scheduler/logs/'

# sub process timeout, need to be same as that in run python package settings
SUB_PROCESS_TIMEOUT = 60 * 15  # 15 mins

# ======================== local settings ======================== #
try:
    from local_settings import *
except ImportError as e:
    pass

try:
    if os.path.exists(CONF_DIR):
        sys.path.insert(0, CONF_DIR)
    from seatable_faas_scheduler_settings import *
except ImportError as e:
    pass
