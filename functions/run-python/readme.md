# Run Python

## Project description

The project is for run-python, including run-python server and the definition of image which python scripts really run in.

We use uwsgi to deploy run-python server which we develop with flask and run python script in container separately.

Here is the introduction of the project files.

- Dockerfile: definition of python-runner
- function.py: flask app
- settings.py: settings of functions
- requirements.txt: requirements of python-runner
- server_requirements.txt: requirements of function
- start.sh: startup script
- stop.sh: stop script


## Deploy

Enter seatable/functions/run-python.

Install requirments flask app

```
pip install -r server_requirements.txt
```

Modify settings.py or create a new `local_settings.py` to set your flask app and modify uwsgi.ini to set uwsgi according to your own needs.

Run start.sh to deploy.

```
./start.sh
```

## Stop

Actually, the serivce is consisted of uwsgi server and docker containers. So, if you want to stop the service, you need to stop uwsgi and related containers.

You can do that by hand or run stop script to do it autimatically.

```
./stop.sh
```
