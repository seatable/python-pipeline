#!/bin/bash

cat $SOURCE_PATH/starter/requirements.txt | grep -vi 'uwsgi' | xargs pip install

set -x
cd $SOURCE_PATH/starter
pylint *.py --disable=all --enable=F,E,W --disable=broad-exception-caught,unspecified-encoding
