ARG BASE_IMAGE="python:3.12-slim-bookworm@sha256:31a416db24bd8ade7dac5fd5999ba6c234d7fa79d4add8781e95f41b187f4c9a"
FROM ${BASE_IMAGE} AS compile-image

# Installation of the pip packages
WORKDIR /opt/scheduler
COPY ["app/requirements.txt", "/opt/scheduler/requirements.txt"]
RUN pip3 install -r /opt/scheduler/requirements.txt --user

### Runtime Image
FROM ${BASE_IMAGE} AS runtime-image

# Clean up && Installation of the apt packages
RUN apt-get update --fix-missing && \
    apt-get upgrade -y && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y \
        tzdata \
        default-mysql-client \
        procps \
        logrotate \
        cron \
        nginx && \
    apt-get autoremove -y && \
    apt-get clean

# copy compiled pip packages in runtime-image
COPY --from=compile-image /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# nginx configuration
COPY ["nginx/nginx.conf", "/etc/nginx/nginx.conf"]
COPY ["nginx/scheduler.conf", "/etc/nginx/conf.d/scheduler.conf"]
RUN rm -rf /etc/nginx/sites-enabled /etc/nginx/sites-available /etc/nginx/conf.d/default.conf

# copy scheduler app
WORKDIR /opt/scheduler
COPY ["app/", "/opt/scheduler/"]
COPY ["version", "/opt/scheduler/version"]
COPY ["logrotate/", "/opt/scheduler/logrotate/"]
RUN mkdir -p /opt/scheduler/logs
RUN mkdir -p /opt/seatable/logs

# Upgrade setuptools to fix vulnerabilities
RUN pip3 install --upgrade setuptools && \
    pip3 install --upgrade --user setuptools && \
    pip3 install -r /opt/scheduler/requirements.txt --user

# Add Tini
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]

# Run your program under Tini
CMD ["/opt/scheduler/entrypoint.sh"]