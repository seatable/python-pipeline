# SeaTable Python Pipeline
This repository contains the Python Pipeline components Scheduler, Starter and Runner.
The Python Pipeline is designed to securely run Python code, to retrieve and deliver the output in the context of SeaTable.
During a typical SeaTable Deployment the images are pulled from Docker Hub by Docker Compose. Please refer to [https://admin.seatable.io](https://admin.seatable.io) for more information.

## Usage
- Clone this repository
- Checkout a new testing branch "testing-v*.*.*"
- Make your changes / Images are being build and pushed automatically after a push or merged pull request.
They use the same repo  as releases, but get the testing- prefix  (seatable/seatable-python-starter, seatable/seatable-python-runner, seatable/seatable-python-scheduler)tag.
- Create new branch "release-v*.*.*" and create a pull request from the testing branch to the release branch.


```mermaid
flowchart
    subgraph Python_Script_Pipeline
        Python_Scheduler --> Python_Starter
        Python_Scheduler <--> MariaDB
        Python_Runner
    end

    Docker_Deamon
    SeaTable_Server --> Python_Scheduler
    Python_Starter --> Docker_Deamon
    Docker_Deamon --> Python_Runner
    Python_Runner <--> SeaTable_Server_API

    note1["Docker Socket mounted via Volume
    priviliged to control the docker daemon
    receives python script via uswgi/function.py"] -.- Python_Starter

    note2["Network exposed or mapped
    Manager / Receiver / Bridge
    formerly FAAS_Scheduler"] -.- Python_Scheduler

    note3["temporary / contains user code / payload
    Gets data from and to SeaTable Server directly via Restful_API"] -.- Python_Runner
```

## Scheduler
A Scheduler for forwarding the requests to run scripts, and responsible for statistics related to the runnign scripts

## Starter
Python Starter is a uswgi/flask container that provides a api to accept request to run a python script, starts a runner docker container in which the script is executed in and posts the output of the script to the scheduler.

## Runner
Python Runner is a container that runs the python script in a sandboxed environment and posts the output of script to the starter via plain text.
[seatable-python-runner python packages](https://github.com/seatable/python-pipeline/blob/main/runner/requirements.txt)
Every time we update [seatable-api](https://pypi.org/project/seatable-api/), we update the runner and starter image so that the latest seatable-api version is included.
