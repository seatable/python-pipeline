#!/bin/bash

# conf
if [ ! -d "/shared/seatable-python-starter/conf" ]; then
    mkdir -p /shared/seatable-python-starter/conf
fi

if [ ! -f "/shared/seatable-python-starter/conf/seatable_python_runner.ini" ]; then
    cp /shared/seatable-python-starter/uwsgi.ini /shared/seatable-python-starter/conf/seatable_python_runner.ini
fi


# logs
if [ ! -d "/shared/seatable-python-starter/logs" ]; then
    mkdir -p /shared/seatable-python-starter/logs
fi

if [ ! -f "/shared/seatable-python-starter/logs/seatable-python-runner.log" ]; then
    touch /shared/seatable-python-starter/logs/seatable-python-runner.log
fi

