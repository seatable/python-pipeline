FROM python:3.7-alpine

RUN apk add openssl-dev gcc musl-dev libxslt-dev libffi-dev

VOLUME [ "/scripts" ]

WORKDIR /scripts

# # install requirements
COPY requirements.txt   .
RUN pip install -r requirements.txt

ENTRYPOINT cat input | python index.py > output
