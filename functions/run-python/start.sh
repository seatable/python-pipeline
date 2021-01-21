#!/bin/bash

if [ ! -d "/var/log" ]; then
    mkdir -p /var/log
fi

if [ ! -f "/var/log/uwsgi.log" ]; then
    touch /var/log/uwsgi.log
fi

uwsgi --ini uwsgi.ini
