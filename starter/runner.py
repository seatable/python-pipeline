import json
import logging
import os
import re
import shutil
import subprocess
import time
import ast
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import requests
from flask import Flask, request, make_response

working_dir = os.getcwd()

# Variables
VERSION = os.environ.get("VERSION")
PYTHON_TRANSFER_DIRECTORY = os.environ.get("PYTHON_TRANSFER_DIRECTORY")
PYTHON_SCHEDULER_URL = os.environ.get("PYTHON_SCHEDULER_URL")
LOG_LEVEL = os.environ.get("PYTHON_STARTER_LOG_LEVEL", "INFO")
TIME_ZONE = os.environ.get("TIME_ZONE", "")
PYTHON_RUNNER_IMAGE = os.environ.get("PYTHON_RUNNER_IMAGE")

THREAD_COUNT = int(os.environ.get("PYTHON_STARTER_THREAD_COUNT", 10))
SUB_PROCESS_TIMEOUT = int(os.environ.get("PYTHON_PROCESS_TIMEOUT", 60 * 15))  # 15 mins
ALTERNATIVE_FILE_SERVER_ROOT = os.environ.get(
    "PYTHON_STARTER_ALTERNATIVE_FILE_SERVER_ROOT", ""
)
USE_ALTERNATIVE_FILE_SERVER_ROOT = os.environ.get(
    "PYTHON_STARTER_USE_ALTERNATIVE_FILE_SERVER_ROOT", ""
)

OUTPUT_LIMIT = int(os.environ.get("PYTHON_RUNNER_OUTPUT_LIMIT", 1000000))
CONTAINER_MEMORY = os.environ.get(
    "PYTHON_RUNNER_CONTAINER_MEMORY", "2g"
)  # default 2G memory for each container/script
CONTAINER_CPUS = os.environ.get("PYTHON_RUNNER_CONTAINER_CPUS", "")
UID = os.environ.get("PYTHON_RUNNER_UID", "")
GID = os.environ.get("PYTHON_RUNNER_GID", "")
USER = os.environ.get("PYTHON_RUNNER_USER", "")
GROUP = os.environ.get("PYTHON_RUNNER_GROUP", "")
NETWORK = os.environ.get("PYTHON_RUNNER_NETWORK", "runner-net")
READ_ONLY_FILESYSTEM = (
    os.environ.get("PYTHON_RUNNER_READ_ONLY_FILESYSTEM", "false").lower() == "true"
)
# 100MB by default
TMPFS_MOUNT_SIZE_IN_BYTES = os.environ.get(
    "PYTHON_RUNNER_TMPFS_MOUNT_SIZE_IN_BYTES", "104857600"
)
DROPPED_CAPABILITIES = [
    cap
    for cap in os.environ.get("PYTHON_RUNNER_DROPPED_CAPABILITIES", "").split(",")
    if cap.strip()
]
NO_NEW_PRIVILEGES = (
    os.environ.get("PYTHON_RUNNER_NO_NEW_PRIVILEGES", "false").lower() == "true"
)
OTHER_OPTIONS = os.environ.get("PYTHON_RUNNER_OTHER_OPTIONS", "[]")
try:
    OTHER_OPTIONS = ast.literal_eval(OTHER_OPTIONS)
except Exception:
    OTHER_OPTIONS = []

# defaults...
LOG_DIR = "/opt/seatable-python-starter/logs/"

# UID/GID of seatable user in python-runner image
SEATABLE_USER_UID = 1000
SEATABLE_USER_GID = 1000


def get_log_level(level):
    if level.lower() == "info":
        return logging.INFO
    elif level.lower() == "warning":
        return logging.WARNING
    elif level.lower() == "debug":
        return logging.DEBUG
    elif level.lower() == "error":
        return logging.ERROR
    elif level.lower() == "critical":
        return logging.CRITICAL
    return logging.INFO


# log to file
def basic_log(log_file):
    if os.environ.get("LOG_TO_STDOUT", "false").lower() == "true":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
    log_level = get_log_level(LOG_LEVEL)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s %(filename)s:%(lineno)s %(funcName)s %(message)s"
    )
    handler.setFormatter(formatter)
    logging.root.setLevel(log_level)
    logging.root.addHandler(handler)


basic_log("starter.log")

app = Flask(__name__)
executor = ThreadPoolExecutor(THREAD_COUNT)
DEFAULT_SUB_PROCESS_TIMEOUT = SUB_PROCESS_TIMEOUT

# timezone command
SYSTEM_TIMEZONE_COMMAND = None
if os.environ.get("TIME_ZONE"):
    SYSTEM_TIMEZONE_COMMAND = ["-e", "TZ=%s" % os.environ.get("TIME_ZONE")]
elif os.path.isfile("/etc/localtime"):
    SYSTEM_TIMEZONE_COMMAND = ["-v", "/etc/localtime:/etc/localtime"]
elif os.path.isfile("/etc/timezone"):
    try:
        with open("/etc/timezone", "r") as time_f:
            time_zone_str = time_f.readline()
    except Exception:
        pass
    else:
        time_zone_str = time_zone_str.strip()
        SYSTEM_TIMEZONE_COMMAND = ["-e", "TZ=%s" % time_zone_str]


def to_python_bool(value):
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return False
    return value.lower() == "true"


def send_to_scheduler(success, return_code, output, spend_time, request_data):
    """
    This function is used to send result of script to scheduler
    - success: whether script running successfully
    - return_code: return-code of subprocess
    - output: output of subprocess or error message
    - spend_time: time subprocess took
    - request_data: data from request
    """

    # prepare data for scheduler
    if output:
        output = output[:OUTPUT_LIMIT]

    url = PYTHON_SCHEDULER_URL.strip("/") + "/script-result/"

    result_data = {
        "success": success,
        "return_code": return_code,
        "output": output,
        "spend_time": spend_time,
    }
    result_data.update(
        {
            "script_id": request_data.get("script_id"),
            "task_log_id": request_data.get("task_log_id"),
        }
    )

    try:
        headers = {"User-Agent": "python-starter/" + VERSION}
        logging.debug("try to send to scheduler: %s, result_data: %s", url, result_data)
        response = requests.post(url, json=result_data, timeout=30, headers=headers)
    except Exception as e:
        logging.error(
            "request could not be send to scheduler: %s. error: %s, result_data: %s",
            url,
            e,
            result_data,
        )
        return

    if response.status_code != 200:
        logging.error(
            "Request did not returned status 200. response: %s, result_data: %s",
            response,
            result_data,
        )


def run_python(data):

    logging.info("New python run initalized... (v%s)", VERSION)

    script_url = data.get("script_url")
    if not script_url:
        send_to_scheduler(False, None, "Script URL is missing", None, data)
        return
    if (
        to_python_bool(USE_ALTERNATIVE_FILE_SERVER_ROOT)
        and ALTERNATIVE_FILE_SERVER_ROOT
    ):
        logging.info("old script_url: %s", script_url)
        script_url = re.sub(
            r"https?://.*?/", ALTERNATIVE_FILE_SERVER_ROOT.strip("/") + "/", script_url
        )
        logging.info("new script_url: %s", script_url)

    # env must be map
    env = data.get("env")
    if env and not isinstance(env, dict):
        env = {}
    env["is_cloud"] = "1"

    timezone_command = None
    # about timezone
    if TIME_ZONE:
        env["TZ"] = TIME_ZONE
    else:
        timezone_command = SYSTEM_TIMEZONE_COMMAND

    # context_data must be a map
    context_data = data.get("context_data")
    if context_data and not isinstance(context_data, dict):
        context_data = None
    context_data = json.dumps(context_data) if context_data else None

    logging.debug("try to get script from seatable server")
    try:
        headers = {"User-Agent": "python-starter/" + VERSION}
        resp = requests.get(script_url, headers=headers, timeout=60)
        logging.debug("response from seatable server: resp: %s", resp)
        if resp.status_code < 200 or resp.status_code >= 300:
            logging.error(
                "Failed to get script from %s, response: %s", script_url, resp
            )
            send_to_scheduler(False, None, "Fail to get script", None, data)
            return
    except Exception as e:
        logging.error("Failed to get script from %s, error: %s", script_url, e)
        send_to_scheduler(False, None, "Fail to get script", None, data)
        return

    logging.debug("Generate temporary random folder directory")
    tmp_id = uuid4().hex
    tmp_dir = os.path.join(PYTHON_TRANSFER_DIRECTORY, tmp_id)
    os.makedirs(tmp_dir)

    if os.path.isdir(tmp_dir):
        logging.debug("Directory created successfully.")
    else:
        logging.error("There was a problem to create the temporary directory")

    # save script
    logging.debug("try to save the script and env.list to the temporary directory")
    try:
        with open(os.path.join(tmp_dir, "index.py"), "wb") as f:
            f.write(resp.content)
        # save env
        env_file = os.path.join(tmp_dir, "env.list")
        with open(env_file, "w") as f:
            if env:
                envs = "\n".join(["%s=%s" % (key, value) for key, value in env.items()])
                f.write(envs)
        # save arguments as file to stdin
        with open(os.path.join(tmp_dir, "input"), "w") as f:
            if context_data:
                f.write(context_data)

        return_code, output = None, ""  # init output
    except Exception as e:
        logging.error("Failed to save script %s, error: %s", script_url, e)
        return

    try:
        logging.debug("Fix ownership of %s", tmp_dir)
        os.chown(tmp_dir, SEATABLE_USER_UID, SEATABLE_USER_GID)
    except Exception as e:
        logging.error("Failed to chown %s, error: %s", tmp_dir, e)
        return

    logging.debug("prepare the command to start the python runner")
    container_name = "python-runner" + tmp_id
    command = [
        "docker",
        "run",
        "--name",
        container_name,
        "--env-file",
        env_file,
        "-v",
        "{}:/scripts".format(tmp_dir),
        "--network",
        NETWORK,
    ]

    # timezone, if not set TIME_ZONE in settings then set time zone use timezone_command
    if timezone_command:
        command.extend(timezone_command)
    # limit memory and cpus
    if CONTAINER_MEMORY:
        command.append("--memory={}".format(CONTAINER_MEMORY))
    if CONTAINER_CPUS:
        command.append("--cpus={}".format(CONTAINER_CPUS))
    user_operation = ""
    # check user
    if USER:
        user_operation += str(USER)
    elif UID:
        user_operation += str(UID)
    # check group
    if user_operation:
        if GROUP:
            user_operation += ":" + str(GROUP)
        elif GID:
            user_operation += ":" + str(GID)
    if user_operation:
        command.extend(["-u", user_operation])
    if READ_ONLY_FILESYSTEM:
        command.append("--read-only")
        # Add tmpfs mount for /tmp (100MB)
        command.extend(
            ["--mount", f"type=tmpfs,dst=/tmp,tmpfs-size={TMPFS_MOUNT_SIZE_IN_BYTES}"]
        )
    if DROPPED_CAPABILITIES:
        command.extend(
            f"--cap-drop={capability}" for capability in DROPPED_CAPABILITIES
        )
    if NO_NEW_PRIVILEGES:
        # Prevent container from gaining additional privileges
        command.extend(["--security-opt", "no-new-privileges"])
    # other options, these options are experimental, may cause failure to start script
    if OTHER_OPTIONS and isinstance(OTHER_OPTIONS, list):
        for option in OTHER_OPTIONS:
            if not isinstance(option, str):
                continue
            if "=" not in option:
                continue
            if "volume" in option and ":/scripts" in option:
                continue
            command.append(option)

    logging.debug("try to execute this python runner image: %s", PYTHON_RUNNER_IMAGE)
    command.append(PYTHON_RUNNER_IMAGE)
    command.append("run")  # override command
    logging.debug("command: %s", command)

    start_at = time.time()

    logging.debug("try to start the python runner image")
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=DEFAULT_SUB_PROCESS_TIMEOUT,
            check=False,
        )
        return_code = result.returncode
        logging.debug("run resulted in this return_code: %s", return_code)
    except subprocess.TimeoutExpired as e:
        try:  # stop container
            subprocess.run(
                ["docker", "stop", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
        except Exception as stop_e:
            logging.warning(
                "stop script: %s container: %s, error: %s",
                script_url,
                container_name,
                stop_e,
            )
        send_to_scheduler(
            False,
            -1,
            "The script's running time exceeded the limit and the execution was aborted.",
            DEFAULT_SUB_PROCESS_TIMEOUT,
            data,
        )
        return
    except Exception as e:
        logging.exception(e)
        logging.error("Failed to run file %s error: %s", script_url, e)
        send_to_scheduler(False, None, None, None, data)
        return
    else:
        logging.debug(
            "python runner should have created an output file in the temporary directory"
        )
        output_file_path = os.path.join(tmp_dir, "output")
        if os.path.isfile(output_file_path):
            if os.path.islink(output_file_path):
                send_to_scheduler(
                    False, -1, "Script invalid!", time.time() - start_at, data
                )
                return
            with open(output_file_path, "r") as f:
                output = f.read()

        if return_code == 137:
            output += "out-of-memory(OOM) error!\n"
            output.error("Out of memory!!!")
        output += result.stdout.decode()
        logging.debug("the output: %s", output)
    finally:
        logging.debug("try to clean up and delete the directory")

        try:
            shutil.rmtree(tmp_dir)
        except Exception as e:
            logging.warning("Fail to remove script files error: %s", e)

        try:
            subprocess.run(
                ["docker", "container", "rm", "-f", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                check=False,
            )
            os.chdir(working_dir)
        except Exception as e:
            logging.warning("Fail to remove container error: %s", e)

    spend_time = time.time() - start_at
    logging.info("python run finished successful. duration was: %s", spend_time)
    logging.debug(
        "send this to the scheduler. return_code: %s, output: %s, spend_time: %s, data: %s",
        return_code,
        output,
        spend_time,
        data,
    )
    send_to_scheduler(return_code == 0, return_code, output, spend_time, data)


####################


@app.route("/ping/", methods=["POST", "GET"])
def ping():
    return make_response(("Pong", 200))


@app.route("/", defaults={"path": ""}, methods=["POST", "GET"])
@app.route("/function/run-python", methods=["POST", "GET"])
def main_route():
    try:
        data = request.get_json()
    except Exception:
        return make_response("Bad Request.", 400)
    try:
        executor.submit(run_python, data)
    except Exception as e:
        logging.error(e)
        return make_response("Internal Server Error.", 500)
    return make_response("Received", 200)


@app.route("/_/health", methods=["POST", "GET"])
def health_check():
    return "Everything is ok."


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8088, debug=False)
