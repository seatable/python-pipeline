#!/bin/bash
#
#

set -o pipefail
set +e

version=`cat /opt/seatable-python-starter/version`
export VERSION=${version}

echo "
*******************
* SEATABLE PYTHON STARTER (v${VERSION})
*******************
"

echo "** Clean old uwsgi and python-runner containers"

# kill old uwsgi
grep_uwsgi_count=`ps aux | grep 'run-pythonuWSGI' | wc -l`
if [ $grep_uwsgi_count -gt 1 ]; then
    ps aux | grep 'run-pythonuWSGI' | grep -v grep | awk '{print $1}' | xargs kill -9
fi

# stop/remove python-runner containers
alive_container_count=`docker ps | grep '$IMAGE' | wc -l`
if [ $alive_container_count -gt 0 ]; then
    docker ps | grep '$IMAGE' | awk '{print $1}' | xargs docker container stop
fi

# remove old python-runner images
container_count=`docker container ls -a | grep '$IMAGE' | wc -l`
if [ $container_count -gt 0 ]; then
    docker container ls -a | grep '$IMAGE' | awk '{print $1}' | xargs docker container rm
fi

# update truststore
echo "Updating CA certificates..."
for cert_file in /usr/local/share/ca-certificates/*.crt; do
  cat "$cert_file" >> "/etc/ssl/certs/ca-certificates.crt"
done
# update-ca-certificates can´t be used in alpine without segmentation of chain in single certificates
# update-ca-certificates --verbose &>> /opt/seatable/logs/init.log


check_empty () {
    if [ -z "$1" ]; then
        echo "$2 is empty ot not defined."
        exit 1
    fi
}

check_starter_config() {
    check_empty "${PYTHON_SCHEDULER_URL}" "PYTHON_SCHEDULER_URL"
    check_empty "${PYTHON_TRANSFER_DIRECTORY}" "PYTHON_TRANSFER_DIRECTORY"
    check_empty "${PYTHON_RUNNER_IMAGE}" "PYTHON_RUNNER_IMAGE"
}


####
check_starter_config

echo "** uWSGI is starting now"
uwsgi --ini /opt/seatable-python-starter/uwsgi.ini 2>&1 &
sleep 1
if curl -IsSf http://127.0.0.1:8080/ping/ >/dev/null 2>&1; then
    echo "** SeaTable Python Starter ready"
else
    echo "** Error: SeaTable Python Starter is not ready. uWSGI is not answering."
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
