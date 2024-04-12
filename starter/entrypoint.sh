#!/bin/bash
#
#

set +e

version=`cat /opt/seatable-python-starter/version`
export VERSION=${version}

echo "
*******************
* SEATABLE PYTHON STARTER (v${VERSION})
*******************
"

# time zone
if [[ $TIME_ZONE != "" ]]; then
    time_zone=/usr/share/zoneinfo/$TIME_ZONE
    echo "$time_zone"
    ls $time_zone
    if [[ ! -e $time_zone ]]; then
        echo "invalid time zone"
        exit 1
    else
        ln -snf $time_zone /etc/localtime
        echo "$TIME_ZONE" > /etc/timezone
    fi
fi

echo "** Clean python-runner containers"

# remove old python-runner images
container_count=`docker container ls -a | grep "$PYTHON_RUNNER_IMAGE" | wc -l`
echo "container count: ${container_count}"
if [ $container_count -gt 0 ]; then
    docker container ls -a | grep "$PYTHON_RUNNER_IMAGE" | awk '{print $1}' | xargs docker container rm -f
fi

# update truststore
echo "Updating CA certificates..."
for cert_file in /usr/local/share/ca-certificates/*.crt; do
  cat "$cert_file" >> "/etc/ssl/certs/ca-certificates.crt"
done
# update-ca-certificates can´t be used in alpine without segmentation of chain in single certificates
# update-ca-certificates --verbose &>> /opt/seatable/logs/init.log


check_empty () {
    if [ -z "$1" ]; then
        echo "$2 is empty ot not defined."
        exit 1
    fi
}

check_starter_config() {
    check_empty "${PYTHON_SCHEDULER_URL}" "PYTHON_SCHEDULER_URL"
    check_empty "${PYTHON_TRANSFER_DIRECTORY}" "PYTHON_TRANSFER_DIRECTORY"
    check_empty "${PYTHON_RUNNER_IMAGE}" "PYTHON_RUNNER_IMAGE"
}


####
check_starter_config

echo "** uWSGI is starting now"
uwsgi --ini /opt/seatable-python-starter/uwsgi.ini 2>&1 &
sleep 1
if curl -IsSf http://127.0.0.1:8080/ping/ >/dev/null 2>&1; then
    echo "** SeaTable Python Starter ready"
else
    echo "** Error: SeaTable Python Starter is not ready. uWSGI is not answering."
fi

# check cron
service cron start &

# logrotate
chmod 0644 /opt/seatable-python-starter/logrotate/logrotate-cron
/usr/bin/crontab /opt/seatable-python-starter/logrotate/logrotate-cron

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
