ARG BASE_IMAGE="python:3.12-slim-bookworm@sha256:31a416db24bd8ade7dac5fd5999ba6c234d7fa79d4add8781e95f41b187f4c9a"
FROM ${BASE_IMAGE} AS compile-image

ARG DOCKER_VERSION="28.1.1"

RUN apt-get update --fix-missing && \
    apt-get upgrade -y && \
    apt-get install -y gcc curl bzip2 unzip

# Get docker binary 
ADD https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz /
RUN tar --extract --file docker-${DOCKER_VERSION}.tgz --directory /tmp/ --strip-components 1

WORKDIR /opt/seatable-python-starter
COPY ["./requirements.txt", "/opt/seatable-python-starter/"]

# Upgrade setuptools to fix vulnerabilities
RUN pip install --upgrade setuptools && \
    pip install --upgrade --user setuptools && \
    pip install -r /opt/seatable-python-starter/requirements.txt --user

### Runtime image
FROM ${BASE_IMAGE} AS runtime-image

RUN apt-get update --fix-missing && \
    apt-get upgrade -y && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y \
        tzdata \
        procps \
        cron \
        logrotate && \
    apt-get autoremove -y && \
    apt-get clean

COPY --from=build-image /tmp/docker /usr/local/bin/docker
RUN chmod +x /usr/local/bin/docker

WORKDIR /opt/seatable-python-starter
COPY ["./", "./"]

# copy compiled pip packages in runtime-image
COPY --from=compile-image /root/.local /root/.local
RUN mkdir -p /opt/seatable-python-starter/logs
ENV PATH=/root/.local/bin:$PATH
ENV LOG_DIR=/opt/seatable-python-starter/logs

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/bash", "/opt/seatable-python-starter/entrypoint.sh"]
