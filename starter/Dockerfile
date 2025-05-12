ARG BASE_IMAGE="python:3.12-slim-bookworm@sha256:31a416db24bd8ade7dac5fd5999ba6c234d7fa79d4add8781e95f41b187f4c9a"
FROM ${BASE_IMAGE} AS compile-image

RUN apt-get update --fix-missing && \
    apt-get install -y gcc

WORKDIR /opt/seatable-python-starter
COPY ["./requirements.txt", "/opt/seatable-python-starter/"]

# Upgrade setuptools to fix vulnerabilities
RUN pip install --upgrade setuptools && \
    pip install --upgrade --user setuptools && \
    pip install -r /opt/seatable-python-starter/requirements.txt --user --break-system-packages

### Runtime image
FROM ${BASE_IMAGE} AS runtime-image

RUN apt-get update --fix-missing && \
    apt-get autoremove -y && \
    apt-get clean && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y tzdata procps cron logrotate docker.io gcc curl

WORKDIR /opt/seatable-python-starter
COPY ["./", "./"]

# copy compiled pip packages in runtime-image
COPY --from=compile-image /root/.local /root/.local
RUN mkdir -p /opt/seatable-python-starter/logs
ENV PATH=/root/.local/bin:$PATH
ENV LOG_DIR=/opt/seatable-python-starter/logs

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/bash", "/opt/seatable-python-starter/entrypoint.sh"]
