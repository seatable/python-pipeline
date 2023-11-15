import os
from uuid import uuid4

DB_HOST = os.getenv('DB_HOST', 'db')
DB_ROOT_PASSWD = os.getenv('DB_ROOT_PASSWD', '')
SCHEDULER_AUTH_TOKEN = os.getenv('PYTHON_SCHEDULER_AUTH_TOKEN', uuid4().hex)

# seatable-faas-scheduler
seatable_faas_scheduler_config_path = '/opt/seatable-faas-scheduler/conf/seatable_faas_scheduler_settings.py'
seatable_faas_scheduler_config = """
# mysql
MYSQL_USER = 'root'
MYSQL_PASSWORD = '%s'
MYSQL_HOST = '%s'
MYSQL_PORT = '3306'
DATABASE_NAME = 'faas_scheduler'

# runner
RUNNER_URL = 'http://seatable-python-starter:8080'

# seatable
DTABLE_WEB_SERVICE_URL = ''
PYTHON_SCHEDULER_AUTH_TOKEN = '%s'  # copy to dtable_web_settings.py

""" % (DB_ROOT_PASSWD, DB_HOST, SCHEDULER_AUTH_TOKEN)

if not os.path.exists(seatable_faas_scheduler_config_path):
    with open(seatable_faas_scheduler_config_path, 'w') as f:
        f.write(seatable_faas_scheduler_config)


# nginx
nginx_config_path = '/opt/seatable-faas-scheduler/conf/nginx.conf'

# init nginx http config
nginx_http_config = """
log_format seatableformat '$http_x_forwarded_for $remote_addr [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $upstream_response_time';

server {
    server_name _;
    listen 80;

    proxy_set_header X-Forwarded-For $remote_addr;

    location / {
        proxy_pass http://localhost:5055;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $server_name;

        access_log      /opt/nginx-logs/seatable-faas-scheduler.access.log seatableformat;
        error_log       /opt/nginx-logs/seatable-faas-scheduler.error.log;
    }
}
"""

if not os.path.exists(nginx_config_path):
    with open(nginx_config_path, 'w') as f:
        f.write(nginx_http_config)

    if not os.path.exists('/etc/nginx/sites-enabled/default'):
        os.system(
            'ln -s /opt/seatable-faas-scheduler/conf/nginx.conf /etc/nginx/sites-enabled/default')
    os.system('nginx -s reload')

print('\nInit config success')
