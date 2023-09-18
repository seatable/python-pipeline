FROM python:3.11-alpine

RUN echo "https://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories
RUN echo "https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories

RUN apk add --upgrade --no-cache \
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

VOLUME [ "/scripts", "/settings" ]

WORKDIR /settings

# install requirements
COPY ./requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt --upgrade --no-cache-dir

# copy entrypoint.sh
COPY ./entrypoint.sh .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/sh", "./entrypoint.sh"]
