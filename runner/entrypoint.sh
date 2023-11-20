#!/bin/sh

# source version
echo "SeaTable Python Runner ready"

#if [[ "$1" != 'custom' ]]; then
if [ -f /scripts/index.py ]; then
    echo "let's run the python code"
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
