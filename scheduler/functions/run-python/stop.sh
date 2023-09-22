#!/bin/bash

# kill uwsgi
# grep 'run-pythonuWSGI' because procname-prefix is set in uwsgi.ini
grep_uwsgi_count=`ps aux | grep 'run-pythonuWSGI' | wc -l`

if [ $grep_uwsgi_count -gt 1 ]; then
    ps aux | grep 'run-pythonuWSGI' | grep -v grep | awk '{print $2}' | xargs kill -9
fi

# stop/remove python-runner containers

alive_container_count=`docker ps | grep 'python-runner' | wc -l`

if [ $alive_container_count -gt 0 ]; then
    docker ps | grep 'python-runner' | awk '{print $1}' | xargs docker container stop
fi

container_count=`docker container ls -a | grep 'python-runner' | wc -l`

if [ $container_count -gt 0 ]; then
    docker container ls -a | grep 'python-runner' | awk '{print $1}' | xargs docker container rm
fi
