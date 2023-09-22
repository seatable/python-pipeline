# Seatable Faas

## FaaS Scheduler
A Scheduler for forwarding the requests to run scripts, and responsible for statistics the data related to scripts running

## Functions
A series of functions, but now there is only run-python which is responsible for running python scripts.


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

#### docker-compose deploy

Deploy `seatable/seatable-faas-scheduler` need a database, we provide a docker-compose.yml in `./faas-scheduler/docker` to deploy a mariadb database container and a faas-scheduler container.

Please note about deploy:

- Change your database password before deploy
- If need to support https, don't close 443 port map
- Since `seatable/seatable-faas-scheduler` is based on ubuntu 22.04, your Docker version need to be 21.10 or greater. If you can't upgrade Docker, you need to open the comment about `security_opt`, some details can read [this blog](https://medium.com/nttlabs/ubuntu-21-10-and-fedora-35-do-not-work-on-docker-20-10-9-1cd439d9921)

```docker-compose
version: '2.0'
services:
  db:
    image: mariadb:10.5
    container_name: seatable-faas-scheduler-mysql
    volumes:
      - "/opt/seatable-faas-scheduler/mysql-data:/var/lib/mysql"  # Requested, specifies the path to MySQL data persistent store.
    environment:
      - MYSQL_ROOT_PASSWORD=PASSWORD  # Requested, set the root's password of MySQL service.
      - MYSQL_LOG_CONSOLE=true
    networks:
      - seatable-faas-scheduler-net

  seatable-faas-scheduler:
    image: seatable/seatable-faas-scheduler:latest
    container_name: seatable-faas-scheduler
    ports:
      - "80:80"
      - "443:443"  # If https is enabled, cancel the comment.
    volumes:
      - /opt/seatable-faas-scheduler/shared:/shared  # Requested, specifies the path to Seafile data persistent store.
    environment:
      - DB_HOST=db
      - DB_ROOT_PASSWD=PASSWORD  # Requested, the value shuold be root's password of MySQL service.
      - SEATABLE_FAAS_SCHEDULER_SERVER_LETSENCRYPT=False # Default is False. Whether to use let's encrypt certificate.
      - SEATABLE_FAAS_SCHEDULER_SERVER_HOSTNAME=demo.faas-scheduler.seatable.cn # Specifies your host name.
      - TIME_ZONE=Etc/UTC # Optional, default is UTC. Should be uncomment and set to your local time zone.
    # security_opt:  # If Docker version <= 20.10.9, please open this
    #   - seccomp:unconfined
    depends_on:
      - db
    networks:
      - seatable-faas-scheduler-net

networks:
  seatable-faas-scheduler-net:

```

### Python Runner

Python runner is a flask server that provides a api to accept request of running python script, run script in a docker container and post the output of script to scheduler.

We provide a code package and some docs to help user to deploy python runner. What content in the package, like following:

- ./functions/run-python/function.py
- ./functions/run-python/init.sh
- ./functions/run-python/server_requirements.txt
- ./functions/run-python/settings.py
- ./functions/run-python/start.sh
- ./functions/run-python/stop.sh
- ./functions/run-python/uwsgi.ini
- ./functions/run-python/version

We suggest you to deploy runner server in uwsgi, so you perhaps need to change some sets about uwsgi in uwsgi.ini for yourself.

The Dockerfile of the image for running script is in `./functions/run-python/docker`. We prepare some python site-packages in image like:

- requests
- seatable-api
- dateutils
- pyOpenSSL
- pandas
- Pillow
- python-barcode

Every time we update [seatable-api](https://pypi.org/project/seatable-api/), we update the runner image so that seatable-api version is the latest.
