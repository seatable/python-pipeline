#!/bin/bash

export SRC_DIR=/opt/seatable-faas-scheduler/
export LD_LIBRARY_PATH=/opt/seatable-faas-scheduler/seafile/lib/
export PYTHONPATH=/opt/seatable-faas-scheduler/seafile/lib/python3.6/site-packages/:/usr/lib/python3.6/dist-packages:/usr/lib/python3.6/site-packages:/usr/local/lib/python3.6/dist-packages:/usr/local/lib/python3.6/site-packages
export PATH=/opt/seatable-faas-scheduler/seafile/bin/:$PATH

export CCNET_CONF_DIR=/opt/seatable-faas-scheduler/ccnet
export SEAFILE_CONF_DIR=/opt/seatable-faas-scheduler/seafile-data
export SEAFILE_CENTRAL_CONF_DIR=/opt/seatable-faas-scheduler/conf


# log function
function log() {
    local time=$(date +"%F %T")
    echo "[$time] $1 "
}

# check process number
# $1 : process name
function check_process() {
    if [ -z $1 ]; then
        log "Input parameter is empty."
        return 0
    fi

    process_num=$(ps -ef | grep "$1" | grep -v "grep" | wc -l)
    echo $process_num
}

# monitor
function monitor_ccnet() {
    process_name="ccnet-server"
    check_num=$(check_process $process_name)
    if [ $check_num -eq 0 ]; then
        log "Start $process_name"
        ccnet-server -F /opt/seatable-faas-scheduler/conf -c /opt/seatable-faas-scheduler/ccnet -f /opt/seatable-faas-scheduler/logs/ccnet.log -d -L /opt/seatable-faas-scheduler -P /opt/seatable-faas-scheduler/pids/ccnet.pid - &
        sleep 0.2
    fi
}

function monitor_seafile() {
    process_name="seaf-server"
    check_num=$(check_process $process_name)
    if [ $check_num -eq 0 ]; then
        log "Start $process_name"
        seaf-server -F /opt/seatable-faas-scheduler/conf -c /opt/seatable-faas-scheduler/ccnet -d /opt/seatable-faas-scheduler/seafile-data -l /opt/seatable-faas-scheduler/logs/seafile.log -L /opt/seatable-faas-scheduler -P /opt/seatable-faas-scheduler/pids/seafile.pid - &
        sleep 0.2
    fi
}

function monitor_flask_server() {
    process_name="flask_server.py"
    check_num=$(check_process $process_name)
    if [ $check_num -eq 0 ]; then
        log "Start $process_name"
        sleep 0.2
        cd /opt/seatable-faas-scheduler/faas-scheduler/
        python3 flask_server.py &>>/opt/seatable-faas-scheduler/logs/flask.log &
        sleep 0.2
    fi
}

function monitor_seatable_faas_scheduler() {
    process_name="scheduler.py"
    check_num=$(check_process $process_name)
    if [ $check_num -eq 0 ]; then
        log "Start $process_name"
        sleep 0.2
        cd /opt/seatable-faas-scheduler/faas-scheduler/
        python3 scheduler.py &>>/opt/seatable-faas-scheduler/logs/scheduler.log &
        sleep 0.2
    fi
}


log "Start Monitor"

while [ 1 ]; do
    monitor_ccnet
    monitor_seafile
    monitor_flask_server
    monitor_seatable_faas_scheduler

    sleep 30
done
