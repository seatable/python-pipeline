import os
from uuid import uuid4

DB_HOST = os.getenv('DB_HOST', 'db')
DB_ROOT_PASSWD = os.getenv('DB_ROOT_PASSWD', '')
SEATABLE_FAAS_SCHEDULER_SERVER_LETSENCRYPT = os.getenv(
    'SEATABLE_FAAS_SCHEDULER_SERVER_LETSENCRYPT', 'False')
SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME = os.getenv(
    'SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME', 'demo.faas-scheduler.seatable.cn')

server_prefix = 'https://' if SEATABLE_FAAS_SCHEDULER_SERVER_LETSENCRYPT == 'True' else 'http://'
SERVER_URL = server_prefix + SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME


# seatable-faas-scheduler
seatable_faas_scheduler_config_path = '/opt/seatable-faas-scheduler/conf/seatable_faas_scheduler_settings.py'
seatable_faas_scheduler_config = """
# mysql
MYSQL_USER = 'root'
MYSQL_PASSWORD = '%s'
MYSQL_HOST = '%s'
MYSQL_PORT = '3306'
DATABASE_NAME = 'faas_scheduler'

# faas
FAAS_URL = ''
SEATABLE_FAAS_AUTH_TOKEN = '%s'

# seatable
FILE_SERVER_ROOT = '%s/seafhttp/'
DTABLE_WEB_SERVICE_URL = '%s'
DTABLE_PRIVATE_KEY = ''
SEATABLE_ADMIN_TOKEN = ''

""" % (DB_ROOT_PASSWD, DB_HOST, str(uuid4()), SERVER_URL, SERVER_URL)

if not os.path.exists(seatable_faas_scheduler_config_path):
    with open(seatable_faas_scheduler_config_path, 'w') as f:
        f.write(seatable_faas_scheduler_config)


# nginx
nginx_config_path = '/opt/seatable-faas-scheduler/conf/nginx.conf'
nginx_common_config = """

    # for letsencrypt
    location /.well-known/acme-challenge/ {
        alias /var/www/challenges/;
        try_files $uri =404;
    }

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

    location /seafhttp {
        rewrite ^/seafhttp(.*)$ $1 break;
        proxy_pass http://127.0.0.1:8082;

        client_max_body_size 0;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_request_buffering off;
        proxy_connect_timeout  36000s;
        proxy_read_timeout  36000s;
        proxy_send_timeout  36000s;

        send_timeout  36000s;

        access_log      /opt/nginx-logs/seafhttp.access.log seatableformat;
        error_log       /opt/nginx-logs/seafhttp.error.log;

    }

}
"""

ssl_dir = '/opt/ssl/'
account_key = ssl_dir + SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME + '.account.key'
domain_key = ssl_dir + SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME + '.key'
domain_csr = ssl_dir + SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME + '.csr'
signed_chain_crt = ssl_dir + SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME + '.crt'


# init nginx https config after init http
def init_https():
    # init letsencrypt
    print('Start init letsencrypt')
    if not os.path.exists(domain_key) or not os.path.exists(signed_chain_crt):
        os.system('mkdir -p /var/www/challenges/')

        if not os.path.exists(account_key):
            os.system('openssl genrsa 4096 > %s' % account_key)
        if not os.path.exists(domain_key):
            os.system('openssl genrsa 4096 > %s' % domain_key)
        if not os.path.exists(domain_csr):
            os.system('openssl req -new -sha256 -key %s -subj "/CN=%s" > %s' %
                      (domain_key, SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME, domain_csr))

        ret = os.system('python3 /scripts/acme-tiny-master/acme_tiny.py --account-key %s --csr %s --acme-dir /var/www/challenges/ > %s' %
                        (account_key, domain_csr, signed_chain_crt))

        if ret != 0:
            os.system('rm -f %s %s' % (signed_chain_crt, nginx_config_path))
            print('\nAuto init letsencrypt failed, delete nginx config anyway.')
            print('Please check your Domain and try again later, now quit.\n')
            import sys
            sys.exit()

        # crontab letsencrypt renew cert
        with open('/opt/ssl/renew_cert', 'w') as f:
            f.write('0 1 1 * * /scripts/renew_cert.sh 2>> /opt/ssl/letsencrypt.log\n')
        os.system('ln -s /opt/ssl/renew_cert /var/spool/cron/crontabs/root')

    #
    nginx_https_config = """
log_format seatableformat '\$http_x_forwarded_for \$remote_addr [\$time_local] "\$request" \$status \$body_bytes_sent "\$http_referer" "\$http_user_agent" \$upstream_response_time';

server {
    if ($host = %s) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name %s;
    return 404;
}

server {
    server_name %s;
    listen 443 ssl;

    ssl_certificate %s;
    ssl_certificate_key %s;
    ssl_session_timeout 5m;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA;
    ssl_session_cache shared:SSL:50m;
    ssl_prefer_server_ciphers on;

""" % (SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME, SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME,
       SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME, signed_chain_crt, domain_key) \
        + nginx_common_config

    with open(nginx_config_path, 'w') as f:
        f.write(nginx_https_config)
    os.system('nginx -s reload')


# init nginx http config
nginx_http_config = """
log_format seatableformat '$http_x_forwarded_for $remote_addr [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $upstream_response_time';

server {
    server_name %s;
    listen 80;

""" % (SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME) + nginx_common_config

if not os.path.exists(nginx_config_path):
    with open(nginx_config_path, 'w') as f:
        f.write(nginx_http_config)

    if not os.path.exists('/etc/nginx/sites-enabled/default'):
        os.system(
            'ln -s /opt/seatable-faas-scheduler/conf/nginx.conf /etc/nginx/sites-enabled/default')
    os.system('nginx -s reload')

    # init https
    if SEATABLE_FAAS_SCHEDULER_SERVER_LETSENCRYPT == 'True' \
            and SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME not in ('', '127.0.0.1'):
        init_https()


print('\nInit config success')
