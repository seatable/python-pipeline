import os


SCHEDULER_URL = ''
SCHEDULER_AUTH_TOKEN = ''
DEBUG = False
IMAGE = os.environ.get('IMAGE')

THREAD_COUNT = 32
SUB_PROCESS_TIMEOUT = 60 * 15  # 15 mins

try:
    from local_settings import *
except:
    pass


assert IMAGE
