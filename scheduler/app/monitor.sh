#!/bin/bash

export PYTHONPATH=/opt/scheduler

LOG_FILE="/opt/scheduler/logs/scheduler.log"

if [ "${LOG_TO_STDOUT:-false}" = "true" ]; then
    LOG_FILE=/proc/1/fd/1
fi

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
        python3 -u flask_server.py >> "${LOG_FILE}" 2>&1 &
        sleep 0.2
    fi
}


log "Start Monitor"

while [ 1 ]; do
    monitor_flask_server

    sleep 30
done
