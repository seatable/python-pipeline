FROM docker:cli

# bash (convenience) and linux-headers (uswgi build dependency) added
# build-essentials to build-base, python3-pip to py3-pip
RUN apk add --no-cache bash \
                       curl \
                       linux-headers \
                       gcc \
                       build-base \
                       python3-dev \
                       py3-pip \
                       unzip

WORKDIR /opt/seatable-python-starter

COPY ./server_requirements.txt /server_requirements.txt
RUN pip install -r /server_requirements.txt

COPY ["./function.py", "./init.sh", "./settings.py", \
 "./start.sh", "./stop.sh", "./uwsgi.ini", "./version", "./"]

RUN ./init.sh

RUN chmod +x ./*.sh

ENTRYPOINT ["./start.sh"]
