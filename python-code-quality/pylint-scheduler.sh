#!/bin/bash

pip install -r $SOURCE_PATH/scheduler/app/requirements.txt

set -x
cd $SOURCE_PATH/scheduler/app
pylint flask_server.py --disable=all --enable=F,E,W --disable=broad-exception-caught
pylint scheduler.py --disable=all --enable=F,E,W --disable=broad-exception-caught
pylint database --disable=all --enable=F,E,W --disable=broad-exception-caught
pylint faas_scheduler --source-roots=["$SOURCE_PATH/scheduler/app"] --disable=all --enable=F,E,W --disable=broad-exception-caught
