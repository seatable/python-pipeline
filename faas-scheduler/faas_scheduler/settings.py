import os
import sys


# mysql
MYSQL_USER = ''
MYSQL_PASSWORD = ''
MYSQL_HOST = ''
MYSQL_PORT = '3306'
DATABASE_NAME = ''

#
FAAS_URL = ''

#
SCHEDULER_INTERVAL = 3600
SCHEDULER_WORKERS = 3

#
DTABLE_PRIVATE_KEY = ''
DTABLE_WEB_SERVICE_URL = ''
INNER_FILE_SERVER_ROOT = 'http://127.0.0.1:8082'

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
    from seatable_thumbnail_settings import *
except ImportError as e:
    pass
