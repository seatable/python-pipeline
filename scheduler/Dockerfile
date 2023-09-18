FROM phusion/baseimage:jammy-1.0.1
# seatable/seatable-faas-scheduler:1.x.x
ENV SCHEDULER_VERSION=

# custom ubuntu source
RUN rm -rf /etc/apt/sources.list
COPY scripts/my-ubuntu-source.list /etc/apt/sources.list

## Dev related libs
RUN apt-get update --fix-missing

# Time zone
RUN export DEBIAN_FRONTEND=noninteractive && apt-get install -y tzdata

# Nginx
RUN apt-get install -y nginx

# Mysql
RUN apt-get install -y mysql-client

RUN apt-get install -y python3-pip
RUN pip3 install flask gevent pyjwt pymysql sqlalchemy==1.4.48 future requests \
    && rm -r /root/.cache/pip


# seatable-faas-scheduler
RUN mkdir -p /opt/seatable-faas-scheduler
WORKDIR /opt/seatable-faas-scheduler
COPY ./faas-scheduler /opt/seatable-faas-scheduler/faas-scheduler
RUN pip3 install -r /opt/seatable-faas-scheduler/faas-scheduler/requirements.txt \
    && rm -r /root/.cache/pip


# scripts
COPY ./scripts /scripts

RUN mkdir -p /etc/service/nginx && \
	rm -f /etc/nginx/sites-enabled/* /etc/nginx/conf.d/* && \
	mv /scripts/nginx.conf /etc/nginx/nginx.conf && \
	mv /scripts/nginx.sh /etc/service/nginx/run

# my_init
RUN rm -rf /etc/my_init.d/*
COPY ./scripts/01_init.sh /etc/my_init.d/01_init.sh
RUN chmod +x /etc/my_init.d/01_init.sh \
	/scripts/*.sh \
	/scripts/*.py

CMD ["/sbin/my_init", "--", "/scripts/enterpoint.sh"]
