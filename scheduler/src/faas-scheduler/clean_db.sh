#!/bin/bash

export PYTHONPATH=/opt/seatable-faas-scheduler/faas-scheduler

python3 /opt/seatable-faas-scheduler/faas-scheduler/faas_scheduler/clean_db.py  &>>/opt/seatable-faas-scheduler/logs/clean_db.log
