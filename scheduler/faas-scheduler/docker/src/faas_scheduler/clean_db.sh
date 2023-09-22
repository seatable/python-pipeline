#!/bin/bash

export PYTHONPATH=/opt/seatable-faas-scheduler/faas-scheduler:/usr/lib/python3.6/dist-packages:/usr/lib/python3.6/site-packages:/usr/local/lib/python3.6/dist-packages:/usr/local/lib/python3.6/site-packages

python3 /opt/seatable-faas-scheduler/faas-scheduler/faas_scheduler/clean_db.py  &>>/opt/seatable-faas-scheduler/logs/clean_db.log
