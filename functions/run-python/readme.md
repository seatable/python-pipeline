# Run Python

## Deploy

Image:

- Aliyun: `registry.cn-beijing.aliyuncs.com/seatable/run-python:latest`

- Aws: `571654986650.dkr.ecr.eu-central-1.amazonaws.com/seatable/run-python:latest`

> Note: Both of URIs of images are the previous URIs.

### K8S

Set environ variables in deployment:

* SCHEDULER_URL: the url of faas-scheduler
* SCHEDULER_AUTH_TOKEN: auth-token of faas-scheduler

And there is an optional variable `DEBUG` which indicates whether program is running in debug mode. Please set `DEBUG` `true` or `false`, default `false`.

### Docker

Please use docker-compose to deploy it.

Before that, please set environ variables in docker-compose.yml file.

```
docker-compose up -d
```
