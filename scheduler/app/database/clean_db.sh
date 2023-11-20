#!/bin/bash

export PYTHONPATH=/opt/scheduler

python3 /opt/scheduler/database/clean_db.py  &>>/opt/scheduler/logs/clean_db.log
