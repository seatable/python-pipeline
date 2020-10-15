#!/bin/bash

function stop_server() {
    pkill -9 -f ccnet-server
    pkill -9 -f seaf-server
    pkill -9 -f flask_server.py
    pkill -9 -f scheduler.py

    pkill -9 -f monitor

    rm -f /opt/seatable-faas-scheduler/pids/*.pid
}

function set_env() {
    export SRC_DIR=/opt/seatable-faas-scheduler/
    export LD_LIBRARY_PATH=/opt/seatable-faas-scheduler/seafile/lib/
    export PYTHONPATH=/opt/seatable-faas-scheduler/seafile/lib/python3.6/site-packages/:/usr/lib/python3.6/dist-packages:/usr/lib/python3.6/site-packages:/usr/local/lib/python3.6/dist-packages:/usr/local/lib/python3.6/site-packages
    export PATH=/opt/seatable-faas-scheduler/seafile/bin/:$PATH

    export CCNET_CONF_DIR=/opt/seatable-faas-scheduler/ccnet
    export SEAFILE_CONF_DIR=/opt/seatable-faas-scheduler/seafile-data
    export SEAFILE_CENTRAL_CONF_DIR=/opt/seatable-faas-scheduler/conf
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

    ccnet-server -F /opt/seatable-faas-scheduler/conf -c /opt/seatable-faas-scheduler/ccnet -f /opt/seatable-faas-scheduler/logs/ccnet.log -d -L /opt/seatable-faas-scheduler -P /opt/seatable-faas-scheduler/pids/ccnet.pid - &
    sleep 0.2

    seaf-server -F /opt/seatable-faas-scheduler/conf -c /opt/seatable-faas-scheduler/ccnet -d /opt/seatable-faas-scheduler/seafile-data -l /opt/seatable-faas-scheduler/logs/seafile.log -L /opt/seatable-faas-scheduler -P /opt/seatable-faas-scheduler/pids/seafile.pid - &
    sleep 0.2

    cd /opt/seatable-faas-scheduler/faas-scheduler/
    python3 flask_server.py &>> /opt/seatable-faas-scheduler/logs/flask.log &
    sleep 0.2

    python3 scheduler.py &>> /opt/seatable-faas-scheduler/logs/scheduler.log &
    sleep 0.2

    /scripts/monitor.sh &>> /opt/seatable-faas-scheduler/logs/monitor.log &

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
