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

if [ ! -d "logs" ]; then
    mkdir -p logs
fi

if [ ! -f "logs/seatable-python-runner.log" ]; then
    touch logs/seatable-python-runner.log
fi

uwsgi --ini uwsgi.ini
