#!/bin/bash

# log function
function log() {
    local time=$(date +"%F %T")
    echo "$time $1 "
    echo "[$time] $1 " &>> /opt/seatable-faas-scheduler/logs/init.log
}


# init config
/etc/my_init.d/01_init.sh

if [ "`ls -A /opt/seatable-faas-scheduler/conf`" = "" ]; then
    log "Start initalization of database and config files. Check init.log if this is the last log entry."
    /scripts/seatable-faas-scheduler.sh init-sql &>> /opt/seatable-faas-scheduler/logs/init.log
    /scripts/seatable-faas-scheduler.sh init &>> /opt/seatable-faas-scheduler/logs/init.log

    # not working
    # echo $SCHEDULER_VERSION > /opt/seatable-faas-scheduler/conf/current_version
else
    log "Initalization skipped, config files already exist."
fi


# check nginx
log "Start nginx ..."
service nginx start & 2>&1 /dev/null

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

if [[ ! -L /etc/nginx/sites-enabled/default ]]; then
    ln -s /opt/seatable-faas-scheduler/conf/nginx.conf /etc/nginx/sites-enabled/default
    nginx -s reload &>> /opt/seatable-faas-scheduler/logs/init.log
fi

# upgrade
log "Check for updates of Python Scheduler ..."
/scripts/upgrade.py


# autorun
echo "Starting SeaTable Python Scheduler ..."
/scripts/seatable-faas-scheduler.sh start
wait
sleep 1

#
# log "This is a idle script (infinite loop) to keep container running."

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
