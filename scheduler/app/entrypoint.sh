#!/bin/bash

set -o pipefail
set +e

version=`cat /opt/scheduler/version`
export VERSION=${version}


# log function
function log() {
    local time=$(date +"%F %T")
    echo "$time $1 "
    echo "[$time] $1 " &>> /opt/scheduler/logs/scheduler.log
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

# database init
echo "Initialize database ..."
python3 /opt/scheduler/database/init_db.py


# upgrade (später wieder einbauen...)
#export CURRENT_VERSION = 
echo "Check for updates of Python Scheduler (${VERSION}) ..."
python3 /opt/scheduler/upgrade/upgrade.py


# check nginx
log "Start nginx ..."
service nginx start &
echo ""

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


# autorun
log "Starting SeaTable Python Scheduler ..."
/opt/scheduler/scheduler.sh start
wait
sleep 1


function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
