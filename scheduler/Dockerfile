### Compile Image
FROM python:3.11-slim-bookworm AS compile-image

# Installation of the pip packages
WORKDIR /opt/scheduler
COPY ["app/requirements.txt", "/opt/scheduler/requirements.txt"]
RUN pip3 install -r /opt/scheduler/requirements.txt --user


### Runtime Image
FROM python:3.11-slim-bookworm AS runtime-image

# Clean up && Installation of the apt packages
RUN apt-get update --fix-missing && \
    apt-get autoremove -y && \
    apt-get clean && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y tzdata default-mysql-client procps cron logrotate nginx

# Comment this line for production
# RUN apt-get install -y curl net-tools nano

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
RUN pip3 install -r /opt/scheduler/requirements.txt --user

# Add Tini
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]

# Run your program under Tini
CMD ["/opt/scheduler/entrypoint.sh"]