# Run Python


## Image:

- seatable/python-runner

If there wasn't on docker hub, please build one with Dockerfile and push it

```
docker build -t="seatable/python-runner:latest" -f Dockerfile .
docker push seatable/python-runner:latest
```

## Deploy

What we need to do to deploy, set flask and run script.

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
