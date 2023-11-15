#!/bin/bash
#
# kill old uwsgi and stop/remove old containers

grep_uwsgi_count=`ps aux | grep 'run-pythonuWSGI' | wc -l`

if [ $grep_uwsgi_count -gt 1 ]; then
    ps aux | grep 'run-pythonuWSGI' | grep -v grep | awk '{print $1}' | xargs kill -9
fi

# stop/remove python-runner containers
alive_container_count=`docker ps | grep '$IMAGE' | wc -l`

if [ $alive_container_count -gt 0 ]; then
    docker ps | grep '$IMAGE' | awk '{print $1}' | xargs docker container stop
fi

container_count=`docker container ls -a | grep '$IMAGE' | wc -l`

if [ $container_count -gt 0 ]; then
    docker container ls -a | grep '$IMAGE' | awk '{print $1}' | xargs docker container rm
fi


##  write config file
if [ ! -f "/shared/seatable-python-starter/conf/seatable_python_runner_settings.py" ]; then
    echo "PYTHON_SCHEDULER_URL = '$PYTHON_SCHEDULER_URL'" >> /shared/seatable-python-starter/conf/seatable_python_runner_settings.py
    echo "IMAGE = '$IMAGE'" >> /shared/seatable-python-starter/conf/seatable_python_runner_settings.py
fi

ln -sn /shared/seatable-python-starter/* /opt/seatable-python-starter

uwsgi --ini /shared/seatable-python-starter/conf/seatable_python_runner.ini


## idle script
echo "This is a idle script (infinite loop) to keep container running."

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
