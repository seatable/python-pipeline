### Compile Image
FROM python:3.11-slim-bookworm AS compile-image

RUN apt-get update --fix-missing && \
    apt-get install -y gcc

WORKDIR /opt/seatable-python-starter
COPY ["./requirements.txt", "/opt/seatable-python-starter/"]

# Upgrade setuptools to fix vulnerabilities
RUN pip install --upgrade setuptools && \
    pip install -r /opt/seatable-python-starter/requirements.txt --user --break-system-packages

### Runtime image
FROM python:3.11-slim-bookworm AS runtime-image

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
