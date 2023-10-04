FROM python:3.11-slim-bullseye AS compile-image

# Installation of the pip packages
WORKDIR /opt/seatable-faas-scheduler
COPY ["src/faas-scheduler/requirements.txt", "./"]
RUN pip3 install -r /opt/seatable-faas-scheduler/requirements.txt --user

## Runtime Image
FROM python:3.11-slim-bullseye AS runtime-image

WORKDIR /opt/seatable-faas-scheduler
COPY ["src/faas-scheduler/", "/opt/seatable-faas-scheduler/faas-scheduler/"]

# seatable/seatable-faas-scheduler:1.x.x
ENV SCHEDULER_VERSION=

# Clean up && Installation of the apt packages
RUN apt-get update --fix-missing && \
    apt-get autoremove -y && \
    apt-get clean && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y tzdata nginx default-mysql-client procps

# copy compiled pip packages in runtime-image
COPY --from=compile-image /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH


COPY ["scripts/", "/scripts/"]

# nginx configuration
RUN mkdir -p /etc/service/nginx && \
	rm -f /etc/nginx/sites-enabled/* /etc/nginx/conf.d/* && \
	mv /scripts/nginx.conf /etc/nginx/nginx.conf && \
	mv /scripts/nginx.sh /etc/service/nginx/run

# my_init
RUN rm -rf /etc/my_init.d/*
COPY scripts/01_init.sh /etc/my_init.d/01_init.sh
RUN chmod +x /etc/my_init.d/01_init.sh \
	/scripts/*.sh \
	/scripts/*.py

ENTRYPOINT ["/scripts/entrypoint.sh"]
