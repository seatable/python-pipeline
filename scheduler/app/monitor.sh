#!/bin/bash

export PYTHONPATH=/opt/scheduler


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
function monitor_flask_server() {
    process_name="flask_server.py"
    check_num=$(check_process $process_name)
    if [ $check_num -eq 0 ]; then
        log "Start $process_name"
        sleep 0.2
        cd /opt/scheduler/
        python3 flask_server.py
        sleep 0.2
    fi
}

function monitor_scheduler() {
    process_name="scheduler.py"
    check_num=$(check_process $process_name)
    if [ $check_num -eq 0 ]; then
        log "Start $process_name"
        sleep 0.2
        cd /opt/scheduler/
        python3 scheduler.py
        sleep 0.2
    fi
}


log "Start Monitor"

while [ 1 ]; do
    monitor_flask_server
    monitor_scheduler

    sleep 30
done
