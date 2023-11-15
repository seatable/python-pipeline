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
    log "Start init"
    /scripts/seatable-faas-scheduler.sh init-sql &>> /opt/seatable-faas-scheduler/logs/init.log
    
    /scripts/seatable-faas-scheduler.sh init &>> /opt/seatable-faas-scheduler/logs/init.log

    echo $SCHEDULER_VERSION > /opt/seatable-faas-scheduler/conf/current_version
else
    log "Conf exists"
fi


# check nginx
service nginx start &

while [ 1 ]; do
    process_num=$(ps -ef | grep "/usr/sbin/nginx" | grep -v "grep" | wc -l)
    if [ $process_num -eq 0 ]; then
        log "Waiting Nginx"
        sleep 0.2
    else
        log "Nginx ready"
        break
    fi
done

if [[ ! -L /etc/nginx/sites-enabled/default ]]; then
    ln -s /opt/seatable-faas-scheduler/conf/nginx.conf /etc/nginx/sites-enabled/default
    nginx -s reload &>> /opt/seatable-faas-scheduler/logs/init.log
fi

# upgrade
/scripts/upgrade.py


# autorun
echo
echo "Starting SeaTable FAAS Scheduler"
echo

/scripts/seatable-faas-scheduler.sh start

wait

sleep 1


#
log "This is a idle script (infinite loop) to keep container running."

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
