import os
import sys
import logging


PYTHON_SCHEDULER_URL = ''

DEBUG = False
LOG_LEVEL = logging.WARNING
IMAGE = os.environ.get('IMAGE')

THREAD_COUNT = 10
SUB_PROCESS_TIMEOUT = 60 * 15  # 15 mins

# Time zone in script container, default UTC
TIME_ZONE = ''

CONTAINER_MEMORY = '2g'  # default 2G memory for each container/script
CONTAINER_CPUS = ''

OUTPUT_LIMIT = 1000000

UID = ''
GID = ''

USER = ''
GROUP = ''

OTHER_OPTIONS = []

ALTERNATIVE_FILE_SERVER_ROOT = ''
USE_ALTERNATIVE_FILE_SERVER_ROOT = False

#
CONF_DIR = 'conf/'
LOG_DIR = 'logs/'

# ======================== local settings ======================== #
try:
    from local_settings import *
except ImportError as e:
    pass

try:
    if os.path.exists(CONF_DIR):
        sys.path.insert(0, CONF_DIR)
    from seatable_python_runner_settings import *
except ImportError as e:
    pass

assert IMAGE
