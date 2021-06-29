FROM python:3.7-alpine

RUN apk add openssl-dev gcc musl-dev python3-dev libxslt-dev libffi-dev cargo
# The reason why install the libs above is that some python libs in requirements need them
# such as pyOpenSSL, depending on cryptography, which needs 'gcc musl-dev python3-dev libffi-dev openssl-dev cargo', saying in its docs
# https://cryptography.io/en/latest/installation.html#alpine

VOLUME [ "/scripts", "/settings" ]

WORKDIR /settings

# install requirements
COPY requirements.txt   .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# copy entrypoint.sh
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/sh", "./entrypoint.sh"]
