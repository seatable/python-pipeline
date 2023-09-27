#!/bin/bash
#
# kill old uwsgi and stop/remove old containers

sh stop.sh

# image="seatable/python-runner-cicd"

# image_count=`docker image ls | awk -vt=: '{print $1t$2}' | grep $image | wc -l`


# if [ $image_count -eq 0 ]; then
#     echo "$image"
#     docker pull $image
# fi

# export IMAGE=$image

if [ ! -f "/shared/conf/seatable_python_runner_settings.py" ]; then
    echo "SCHEDULER_URL = '$PYTHON_SCHEDULER_SCHEME$PYTHON_SCHEDULER_HOSTNAME:$PYTHON_SCHEDULER_PORT'" >> /shared/conf/seatable_python_runner_settings.py
    echo "IMAGE = '$IMAGE'" >> /shared/conf/seatable_python_runner_settings.py
fi

ln -sn /shared/* /opt/seatable-python-starter

uwsgi --ini /shared/conf/seatable_python_runner.ini

#
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

