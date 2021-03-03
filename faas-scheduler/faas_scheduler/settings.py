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
FAAS_URL = ''

#
DTABLE_WEB_SERVICE_URL = ''
SEATABLE_FAAS_AUTH_TOKEN = ''

#
CONF_DIR = '/opt/seatable-faas-scheduler/conf/'
LOG_DIR = '/opt/seatable-faas-scheduler/logs/'

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
