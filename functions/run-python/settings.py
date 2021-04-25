import os
import sys


SCHEDULER_URL = ''

DEBUG = False
IMAGE = os.environ.get('IMAGE')

THREAD_COUNT = 10
SUB_PROCESS_TIMEOUT = 60 * 15  # 15 mins

CONTAINER_MEMORY = '2g'  # default 2G memory for each container/script
CONTAINER_CPUS = ''

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
