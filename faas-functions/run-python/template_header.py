import os

from seatable_api import SeaTableAPI as Base


server_url = os.environ.get('dtable_web_url')
api_token = os.environ.get('api_token')

base = Base(api_token, server_url)

base.auth()
