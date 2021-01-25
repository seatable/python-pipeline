#!/bin/bash

helpFunction()
{
    echo "start.sh -p [aws/aliyun]"
}

while getopts p: opt;
do
    case $opt in
        p) platform="$OPTARG"
        ;;
        ?) helpFunction
        ;;
    esac
done

echo "platform: $platform"

if [ "$platform" == "aws" ]; then
    image="571654986650.dkr.ecr.eu-central-1.amazonaws.com/seatable/docker-python:latest"
elif [ "$platform" == "aliyun" ]; then
    image="registry.cn-beijing.aliyuncs.com/seatable/docker-python:latest"
else
    echo "platform invalid"
    exit 1
fi

echo "$image"

docker pull $image
export IMAGE=$image

pip3 install -r server_requirements.txt

if [ ! -d "/var/log" ]; then
    mkdir -p /var/log
fi

if [ ! -f "/var/log/uwsgi.log" ]; then
    touch /var/log/uwsgi.log
fi

uwsgi --ini uwsgi.ini
