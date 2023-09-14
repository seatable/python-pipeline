#!/bin/bash

# conf
if [ ! -d "conf" ]; then
    mkdir -p conf
fi

if [ ! -f "conf/seatable_python_runner_settings.py" ]; then
    echo "SCHEDULER_URL = ''" >> conf/seatable_python_runner_settings.py
fi

if [ ! -f "conf/seatable_python_runner.ini" ]; then
    cp uwsgi.ini conf/seatable_python_runner.ini
fi


# logs
if [ ! -d "logs" ]; then
    mkdir -p logs
fi

if [ ! -f "logs/seatable-python-runner.log" ]; then
    touch logs/seatable-python-runner.log
fi
