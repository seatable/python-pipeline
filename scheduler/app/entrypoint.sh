#!/bin/bash

set -e


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

# initilization of database (get version from database)
# ...

#if [ "`ls -A /opt/scheduler/conf`" = "" ]; then
#    log "Start initalization of database and config files."
#    /opt/scheduler/scripts/seatable-faas-scheduler.sh init-sql
#    #/scripts/seatable-faas-scheduler.sh init

    # not working
    # echo $SCHEDULER_VERSION > /opt/seatable-faas-scheduler/conf/current_version
#else
#    log "Initalization skipped, config files already exist."
#fi

# upgrade (später wieder einbauen...)
#log "Check for updates of Python Scheduler ..."
#/scripts/upgrade.py


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
