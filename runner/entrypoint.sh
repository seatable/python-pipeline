#!/bin/sh

if [ -f /scripts/index.py ]; then
    cd /scripts
    cat input | python index.py > output
    exit $?
else
    echo "No input file found"
    echo "Goodbye"
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
