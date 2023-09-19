#!/bin/bash
#
# kill old uwsgi and stop/remove old containers
cp -rn /init/* /opt/seatable-python-starter

cd /opt/seatable-python-starter

sh stop.sh

image="seatable/python-runner-cicd"

image_count=`docker image ls | awk -vt=: '{print $1t$2}' | grep $image | wc -l`


if [ $image_count -eq 0 ]; then
    echo "$image"
    docker pull $image
fi

export IMAGE=$image

if [ ! -f "conf/seatable_python_runner.ini" ]; then
    /init/init.sh
fi

uwsgi --ini conf/seatable_python_runner.ini

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
