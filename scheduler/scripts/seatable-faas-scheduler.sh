#!/bin/bash

function stop_server() {
    pkill -9 -f flask_server.py
    pkill -9 -f scheduler.py

    pkill -9 -f monitor

    rm -f /opt/seatable-faas-scheduler/pids/*.pid
}

function set_env() {
    export PYTHONPATH=/opt/seatable-faas-scheduler/faas-scheduler:/usr/local/lib/python3.11/site-packages
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
    python3 flask_server.py &>>/opt/seatable-faas-scheduler/logs/faas-scheduler.log &
    sleep 0.2

    python3 scheduler.py &>>/opt/seatable-faas-scheduler/logs/faas-scheduler.log &
    sleep 0.2

    /scripts/monitor.sh &>>/opt/seatable-faas-scheduler/logs/monitor.log &

    echo
    echo "SeaTable FAAS Scheduler started"
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


function upgrade_sql() {
    if [ ! $DB_ROOT_PASSWD ]; then
        mysql -h $DB_HOST -p$DB_ROOT_PASSWD faas_scheduler </opt/seatable-faas-scheduler/faas-scheduler/upgrade/${*:2}.sql
    else
        mysql -h $DB_HOST -u$DB_USER -p$DB_PASSWD faas_scheduler </opt/seatable-faas-scheduler/faas-scheduler/upgrade/${*:2}.sql
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
"init-sql")
    init_sql
    ;;
"init")
    init
    ;;
"upgrade-sql")
    upgrade_sql "$@"
    ;;
*)
    start_server
    ;;
esac
