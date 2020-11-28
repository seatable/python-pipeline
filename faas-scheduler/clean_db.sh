#!/bin/bash

export SRC_DIR=/opt/seatable-faas-scheduler/
export LD_LIBRARY_PATH=/opt/seatable-faas-scheduler/seafile/lib/
export PYTHONPATH=/opt/seatable-faas-scheduler/faas-scheduler:/opt/seatable-faas-scheduler/seafile/lib/python3.6/site-packages/:/usr/lib/python3.6/dist-packages:/usr/lib/python3.6/site-packages:/usr/local/lib/python3.6/dist-packages:/usr/local/lib/python3.6/site-packages
export PATH=/opt/seatable-faas-scheduler/seafile/bin/:$PATH
export CCNET_CONF_DIR=/opt/seatable-faas-scheduler/ccnet
export SEAFILE_CONF_DIR=/opt/seatable-faas-scheduler/seafile-data
export SEAFILE_CENTRAL_CONF_DIR=/opt/seatable-faas-scheduler/conf

python3 /opt/seatable-faas-scheduler/faas-scheduler/faas_scheduler/clean_db.py  &>>/opt/seatable-faas-scheduler/logs/clean_db.log
