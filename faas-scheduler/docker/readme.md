# seatable-faas-scheduler-docker

## Deploy

1. mkdir -p /opt/seatable-faas-scheduler/shared/
2. mkdir -p /opt/seatable-faas-scheduler/mysql-data/
3. vim /opt/seatable-faas-scheduler/docker-compose.yml
4. docker-compose up
5. vim /opt/seatable-faas-scheduler/shared/seatable-faas-scheduler/conf/*
6. vim /opt/seatable-faas-scheduler/shared/seatable-faas-scheduler/seafile-license.txt
7. docker exec -d seatable-faas-scheduler /scripts/seatable-faas-scheduler.sh

## Build

1. cp faas_scheduler docker/src/faas-scheduler/faas_scheduler
2. cp flask_server.py docker/src/faas-scheduler/flask_server.py
3. cp scheduler.py docker/src/faas-scheduler/scheduler.py
4. cp mysql.sql docker/src/faas-scheduler/mysql.sql
5. cp seafile docker/src/seafile (seafile folder was in seatable-pro-server_1.x.x.tar.gz)
6. docker build -t docker.seafile.top/seafile-dev/seatable-faas-scheduler:1.x.x ./
