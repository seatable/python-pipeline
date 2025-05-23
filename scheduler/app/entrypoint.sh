#!/bin/bash

set -o pipefail
set +e

version=`cat /opt/scheduler/version`
export VERSION=${version}

LOG_FILE="/opt/scheduler/logs/scheduler.log"
INIT_LOG_FILE="/opt/seatable/logs/init.log"

if [ "${LOG_TO_STDOUT:-false}" = "true" ]; then
    LOG_FILE=/proc/1/fd/1
    INIT_LOG_FILE=/proc/1/fd/1
fi

# log function
function log() {
    local time=$(date +"%F %T")
    echo "$time $1 "
    echo "[$time] $1 " &>> "{LOG_FILE}"
}

# time zone
if [[ $TIME_ZONE != "" ]]; then
    time_zone=/usr/share/zoneinfo/$TIME_ZONE
    if [[ ! -e $time_zone ]]; then
        echo "invalid time zone"
        exit 1
    else
        ln -snf $time_zone /etc/localtime
        echo "$TIME_ZONE" > /etc/timezone
    fi
fi

sed -i '$a\PATH=/opt/scheduler:$PATH' ~/.bashrc
chmod u+x /opt/scheduler/*.sh

echo "
*******************
* SEATABLE PYTHON SCHEDULER (v${VERSION})
*******************
"

# database init
echo "Initialize database ..."
python3 /opt/scheduler/database/init_db.py

# upgrade (später wieder einbauen...)
#export CURRENT_VERSION =
echo "Check for updates of Python Scheduler ..."
python3 /opt/scheduler/upgrade/upgrade.py

# update truststore
# segmentation of chain in single certificates neccecary only on alpine
log "Updating CA certificates..."
update-ca-certificates --verbose &>> "${INIT_LOG_FILE}"

# check nginx
log "Start nginx ..."
service nginx start &

while [ 1 ]; do
    sleep 0.2
    process_num=$(ps -ef | grep "/usr/sbin/nginx" | grep -v "grep" | wc -l)
    if [ $process_num -eq 0 ]; then
        log "Waiting for nginx to start ..."
    else
        log "nginx ready"
        break
    fi
done

# check cron
log "Start cron"
service cron start &

# logrotate
chmod 0644 /opt/scheduler/logrotate/logrotate-cron
/usr/bin/crontab /opt/scheduler/logrotate/logrotate-cron

# autorun
log "Starting SeaTable Python Scheduler ..."
/opt/scheduler/scheduler.sh start
wait
sleep 1

# check if all variables are set correctly
# later...

# healthcheck
# later...

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
