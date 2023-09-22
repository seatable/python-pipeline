#!/bin/sh

if [[ "$1" != 'custom' ]]; then
    cd /scripts
    cat input | python index.py > output
    exit $?
fi

function cleanup() {
    kill -s SIGTERM $!
    exit 0
}

trap cleanup SIGINT SIGTERM

while [ 1 ]; do
    sleep 60 &
    wait $!
done
