# seatable-faas-scheduler-docker

## Deploy

1. mkdir -p /opt/seatable-faas-scheduler/shared/
2. mkdir -p /opt/seatable-faas-scheduler/mysql-data/
3. vim /opt/docker-compose.yml
4. docker-compose up
5. vim /opt/seatable-faas-scheduler/shared/seatable-faas-scheduler/conf/*
6. vim /opt/seatable-faas-scheduler/shared/seatable-faas-scheduler/seafile-license.txt
7. docker exec -d seatable-faas-scheduler /scripts/seatable-faas-scheduler.sh

## Build

1. cp `code files` docker/src/faas-scheduler/
2. docker build -t seatable/seatable-faas-scheduler:1.x.x ./
