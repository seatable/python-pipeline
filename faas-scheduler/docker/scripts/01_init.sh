#!/bin/bash

set -e

# time zone
if [[ $TIME_ZONE != "" ]]; then
    time_zone=/usr/share/zoneinfo/$TIME_ZONE
    if [[ ! -e $time_zone ]]; then
        echo "invalid time zone"
        exit 1
    else
        ln -snf $time_zone /etc/localtime
        echo "$TIME_ZONE" > /etc/timezone
    fi
fi

# check folder
if [[ ! -e /shared ]]; then
    echo 'do not find /shared path'
    exit 1
fi

if [[ ! -e /shared/nginx-logs ]]; then
    mkdir /shared/nginx-logs
fi

if [[ ! -e /shared/ssl ]]; then
    mkdir /shared/ssl
fi

if [[ ! -e /shared/seatable-faas-scheduler ]]; then
    mkdir /shared/seatable-faas-scheduler
fi

if [[ ! -e /shared/seatable-faas-scheduler/conf ]]; then
    mkdir /shared/seatable-faas-scheduler/conf
fi

if [[ ! -e /shared/seatable-faas-scheduler/logs ]]; then
    mkdir /shared/seatable-faas-scheduler/logs
fi

# seatable.sh
if [[ ! -e /shared/seatable-faas-scheduler/scripts ]]; then
    mkdir /shared/seatable-faas-scheduler/scripts
fi

if [[ -f /shared/seatable-faas-scheduler/scripts/seatable-faas-scheduler.sh ]]; then
    cp /shared/seatable-faas-scheduler/scripts/seatable-faas-scheduler.sh /shared/seatable-faas-scheduler/scripts/seatable-faas-scheduler.sh.bak
fi

cp /scripts/seatable-faas-scheduler.sh /shared/seatable-faas-scheduler/scripts/seatable-faas-scheduler.sh
sed -i '$a\PATH=/opt/seatable-faas-scheduler/scripts:$PATH' ~/.bashrc
chmod u+x /shared/seatable-faas-scheduler/scripts/*.sh

# main
ln -sfn /shared/seatable-faas-scheduler/* /opt/seatable-faas-scheduler
ln -sfn /shared/nginx-logs /opt
ln -sfn /shared/ssl /opt
