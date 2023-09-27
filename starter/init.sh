#!/bin/bash

# conf
if [ ! -d "/shared/conf" ]; then
    mkdir -p /shared/conf
fi

if [ ! -f "/shared/conf/seatable_python_runner.ini" ]; then
    cp /shared/uwsgi.ini /shared/conf/seatable_python_runner.ini
fi


# logs
if [ ! -d "/shared/logs" ]; then
    mkdir -p /shared/logs
fi

if [ ! -f "/shared/logs/seatable-python-runner.log" ]; then
    touch /shared/logs/seatable-python-runner.log
fi
