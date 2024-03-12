#!/bin/bash
#
# builds the python-code-quality image if necessesary and runs black & pylint locally

set -euo pipefail

# FIXME only fixable on system level.
# sudo calls should be removed. Addinng the local user in the docker group is preferred.

image_name="python-code-quality"

if sudo docker inspect "${image_name}" &> /dev/null; then
  container_id=$(sudo docker create "${image_name}")

  if [ ! -f python-code-quality/requirements_frozen.txt ]; then
    sudo docker cp "${container_id}:/app/requirements_frozen.txt" python-code-quality/requirements_frozen.txt
  fi

  if ! sudo docker cp "${container_id}:/app/requirements_frozen.txt" - | \
  tar x -O | \
  diff -w python-code-quality/requirements_frozen.txt - > \
  /dev/null; then
    sudo docker build -t "${image_name}" python-code-quality/
  fi

  sudo docker rm "${container_id}"
else
  sudo docker build -t "${image_name}" python-code-quality/
fi

sudo docker run -v "`pwd`":/app/ --rm "${image_name}" black /app/

echo 'pylint scheduler app'
sudo docker run -v "`pwd`":/app/ --rm "${image_name}" bash -c "
pip install -r /app/scheduler/app/requirements.txt

set -x
cd /app/scheduler/app
pylint flask_server.py --disable=all --enable=W,E --disable=broad-exception-caught
pylint scheduler.py --disable=all --enable=W,E --disable=broad-exception-caught
pylint database --disable=all --enable=W,E --disable=broad-exception-caught
pylint faas_scheduler --source-roots=['database', 'faas_scheduler'] --disable=all --enable=W,E --disable=broad-exception-caught
"

echo ''pylint starter
sudo docker run -v "`pwd`":/app/ --rm "${image_name}" bash -c "
cat /app/starter/requirements.txt | grep -vi 'uwsgi' | xargs pip install

set -x
cd /app/starter
pylint *.py --disable=all --enable=W,E --disable=broad-exception-caught,unspecified-encoding
"
