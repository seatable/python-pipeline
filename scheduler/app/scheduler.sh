#!/bin/bash

function stop_server() {
    pkill -9 -f flask_server.py
    pkill -9 -f scheduler.py
    pkill -9 -f monitor
    rm -f /opt/scheduler/pids/*.pid
}

function set_env() {
    export PYTHONPATH=/opt/scheduler
}

function run_python_wth_env() {
    set_env
    python3 ${*:2}
}

function start_server() {
    set_env

    stop_server
    sleep 0.5

    cd /opt/scheduler/
    python3 flask_server.py &
    # &>>/opt/scheduler/logs/scheduler2.log &
    sleep 0.2

    python3 scheduler.py &
    # &>>/opt/scheduler/logs/scheduler3.log &
    sleep 0.2

    ./monitor.sh &
    #&>>/opt/scheduler/logs/monitor.log &

    echo "SeaTable Python Scheduler ready"
}


function upgrade_sql() {
    if [ ! $DB_ROOT_PASSWD ]; then
        mysql -h $DB_HOST -u$DB_USER -p$DB_PASSWD faas_scheduler </opt/scheduler/upgrade/${*:2}.sql
    else
        mysql -h $DB_HOST -p$DB_ROOT_PASSWD faas_scheduler </opt/scheduler/upgrade/${*:2}.sql
    fi
}


case $1 in
"start")
    start_server
    ;;
"python-env")
    run_python_wth_env "$@"
    ;;
"stop")
    stop_server
    ;;
"restart")
    stop_server
    start_server
    ;;
"upgrade-sql")
    upgrade_sql "$@"
    ;;
*)
    start_server
    ;;
esac
