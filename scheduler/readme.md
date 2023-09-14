# faas-scheduler

`python3 flask_server.py`

`python3 scheduler.py`

## Development

Scheduler apis are held in `./faas-scheduler/flask-server.py` with gevent WSGIServer, and run script api is in `./function/run-python`

## Publish and deploy

### FaaS Scheduler

#### Dockerfile

Scheduler is deployed in docker, the Dockerfile in `./faas-schduler/docker` describes more details about image. `phusion/baseimage:jammy-1.0.1`, which is based on ubuntu 22.04, is the base image of `seatable/seatable-fass-scheduler`.

#### docker build

After development completed, make a directory `./faas-scheduler/docker/src/faas-scheduler`, and copy following directorys and files there.

- ./faas-scheduler/faas_scheduler
- ./faas-scheduler/upgrade
- ./faas-scheduler/clean_db.sh
- ./faas-scheduler/flask_server.py
- ./faas-scheduler/mysql.sql
- ./faas-scheduler/readme.md
- ./faas-scheduler/requirements.txt
- ./faas-scheduler/scheduler.py

Run command `docker build -t seatable/seatable-faas-scheduler:xxx` in `./faas-scheduler/docker` path.

After build, Run command `docker push seatable/seatable-faas-scheduler:xxx` to publish new image.