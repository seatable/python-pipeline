#!/bin/bash

function stop_server() {
    pkill -9 -f flask_server.py
    pkill -9 -f scheduler.py

    pkill -9 -f monitor

    rm -f /opt/seatable-faas-scheduler/pids/*.pid
}

function set_env() {
    export PYTHONPATH=/opt/seatable-faas-scheduler/faas-scheduler:/usr/lib/python3.6/dist-packages:/usr/lib/python3.6/site-packages:/usr/local/lib/python3.6/dist-packages:/usr/local/lib/python3.6/site-packages
}

function run_python_wth_env() {
    set_env
    python3 ${*:2}
}

function check_folder() {
    if [[ ! -e /opt/seatable-faas-scheduler/conf ]]; then
        echo 'do not find /opt/seatable-faas-scheduler/conf path'
        exit 1
    fi
}

function start_server() {

    check_folder

    stop_server
    sleep 0.5

    set_env

    cd /opt/seatable-faas-scheduler/faas-scheduler/
    python3 flask_server.py &>>/opt/seatable-faas-scheduler/logs/web_server.log &
    sleep 0.2

    python3 scheduler.py &>>/opt/seatable-faas-scheduler/logs/scheduler.log &
    sleep 0.2

    /scripts/monitor.sh &>>/opt/seatable-faas-scheduler/logs/monitor.log &

    echo "SeaTable-faas-scheduler started"
    echo

}


function init_sql() {
    set_env

    python3 /scripts/init_sql.py

}


function init() {
    if [[ ! -e /opt/seatable-faas-scheduler/conf ]]; then
        mkdir /opt/seatable-faas-scheduler/conf
    fi

    set_env

    python3 /scripts/init_config.py

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
"init-sql")
    init_sql
    ;;
"init")
    init
    ;;
*)
    start_server
    ;;
esac
