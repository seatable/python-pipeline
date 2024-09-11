FROM python:3.11-alpine AS compile-image

RUN apk add --no-cache \
        cargo \
        freetype-dev \
        fribidi-dev \
        g++ \
        gcc \
        harfbuzz-dev \
        jpeg-dev \
        lcms2-dev \
        libffi-dev \
        libimagequant-dev \
        libpng-dev \
        libwebp-dev \
        libxcb-dev \
        libxslt-dev \
        musl-dev \
        openjpeg-dev \
        openssl-dev \
        python3-dev \
        tcl-dev \
        tiff-dev \
        tk-dev \
        zlib-dev

VOLUME [ "/scripts" ]

WORKDIR /settings

COPY ./requirements.txt .

# Upgrade setuptools to fix vulnerabilities
RUN pip install --upgrade --user setuptools && \
    pip install -r requirements.txt --no-cache-dir --user


## Runtime image
FROM python:3.11-alpine AS runtime-image

RUN apk add --no-cache bash \
                       python3-dev

RUN adduser -D seatable
USER seatable
WORKDIR /home/seatable

COPY --from=compile-image --chown=seatable /root/.local /home/seatable/.local
ENV PATH=/home/seatable/.local/bin:$PATH

COPY --chown=seatable ./entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/sh", "./entrypoint.sh"]
