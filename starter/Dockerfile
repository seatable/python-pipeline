ARG IMAGE=docker:24.0.7-cli
ARG IMAGE_DIGEST=sha256:8a5e8d1346479822d16cd0de1b61d3f0e623c41f0240b54736780c4c47f75527

## Compile Image
FROM ${IMAGE}@${IMAGE_DIGEST} AS compile-image

# bash (convenience) and linux-headers (uswgi build dependency) added
# build-essentials to build-base, python3-pip to py3-pip
RUN apk add --no-cache unzip \
                       python3-dev \
                       py3-pip \
                       linux-headers \
                       gcc \
                       build-base

WORKDIR /opt/seatable-python-starter
COPY ["./requirements.txt", "/opt/seatable-python-starter/"]
RUN pip install -r /opt/seatable-python-starter/requirements.txt --user --break-system-packages

#####

## Runtime image
FROM ${IMAGE}@${IMAGE_DIGEST} AS runtime-image

RUN apk add --no-cache bash \
                       curl \
                       python3-dev



WORKDIR /opt/seatable-python-starter
COPY ["./", "./"]
#COPY ["./entrypoint.sh", "./"]
#COPY ["./runner.py", "./"]
#COPY ["./uwsgi.ini", "./"]

# copy compiled pip packages in runtime-image
COPY --from=compile-image /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/sh", "/opt/seatable-python-starter/entrypoint.sh"]
