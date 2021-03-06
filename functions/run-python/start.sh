#!/bin/bash

# kill old uwsgi and stop/remove old containers
sh stop.sh

image="seatable/python-runner:latest"

image_count=`docker image ls | awk -vt=: '{print $1t$2}' | grep $image | wc -l`


if [ $image_count -eq 0 ]; then
    echo "$image"
    docker pull $image
fi

export IMAGE=$image

if [ ! -f "conf/seatable_python_runner.ini" ]; then
    ./init.sh
fi

uwsgi --ini conf/seatable_python_runner.ini
