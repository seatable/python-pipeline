# Run Python


## Image:

- Aliyun: `registry.cn-beijing.aliyuncs.com/seatable/docker-python:latest`

- Aws: `571654986650.dkr.ecr.eu-central-1.amazonaws.com/seatable/docker-python:latest`

If there isn't one image on aliyun/aws, please build one and push it with Dockerfile

```
docker build -t="registry.cn-beijing.aliyuncs.com/seatable/docker-python:latest" -f Dockerfile .
docker push registry.cn-beijing.aliyuncs.com/seatable/docker-python:latest
```

## Deploy

What we need to do to deploy, including set flask and run script.

First, go to path seatable-faas/functions/run-python, touch a new file local_settings.py to set some options such as scheduler url, sheduler token and so on.

```
SCHEDULER_URL = ''
SCHEDULER_AUTH_TOKEN = ''

THREAD_COUNT = 32         # count of threads
SUB_PROCESS_TIMEOUT = 60  # timeout of subprocess running
```

Then, run start.sh script like following.

```
./start.sh -p [aliyun/aws]
```

If you are on an aliyun machine, `./start.sh -p aliyun`.

Similarly, `./start.sh -p aws` if you are on an aws machine.
