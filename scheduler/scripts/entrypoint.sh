#!/bin/bash

# log function
function log() {
    local time=$(date +"%F %T")
    echo "$time $1 "
    echo "[$time] $1 " &>> /opt/seatable-faas-scheduler/logs/faas-scheduler.log
}


# init config
/etc/my_init.d/01_init.sh

if [ "`ls -A /opt/seatable-faas-scheduler/conf`" = "" ]; then
    log "Start initalization of database and config files."
    /scripts/seatable-faas-scheduler.sh init-sql
    #/scripts/seatable-faas-scheduler.sh init

    # not working
    # echo $SCHEDULER_VERSION > /opt/seatable-faas-scheduler/conf/current_version
else
    log "Initalization skipped, config files already exist."
fi

# upgrade
log "Check for updates of Python Scheduler ..."
/scripts/upgrade.py


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
/scripts/seatable-faas-scheduler.sh start
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
