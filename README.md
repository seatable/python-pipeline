# SeaTable Python Pipeline
This repository contains the Python Pipeline components Scheduler, Starter and Runner.
The Python Pipeline is designed to securely run Python code, to retrieve and deliver the output in the context of SeaTable.
During a typical SeaTable Deployment the images are pulled from Docker Hub by Docker Compose. Please refer to [https://admin.seatable.io](https://admin.seatable.io) for more information.

## Usage
- Clone this repository
- Checkout a new feature/testing branch "wip/xxx" or "testing/xxx"
- Tag commits with the corresponding testing tags
  - `testing-runner-v*.*.*`
  - `testing-scheduler-v*.*.*`
  - `testing-starter-v*.*.*`

- Merge the testing branch into main via pull request

- Tag the commit on main with the corresponding release tags
  - `release-runner-v*.*.*`
  - `release-scheduler-v*.*.*`
  - `release-starter-v*.*.*`

 Images are being build and pushed to dockerhub automatically after a tag is pushed to the remote origin.
 Build from testing tags get the "testing-" prefix, build numbers and commit ids are used for additional tags.

 ```bash
git tag testing-runner-v*.*.*
git push origin testing-runner-v*.*.*
## you can create and push multiple tags on the same commit
git tag testing-scheduler-v*.*.*
git tag testing-starter-v*.*.*
git tag testing-runner-v*.*.*
git push origin --tags # push them all at once
 ```
## Architecture Overview
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
