FROM python:3.7-alpine

RUN apk add openssl-dev gcc musl-dev libxslt-dev libffi-dev


WORKDIR /root

# install requirements
COPY requirements.txt   .
RUN pip install -r requirements.txt

COPY function.py          .
COPY start.sh             .
COPY uwsgi.ini            .
COPY entrypoint.sh        .



RUN chmod +x start.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT sh start.sh && sh entrypoint.sh
