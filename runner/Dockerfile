
ARG IMAGE=python:3.11-alpine
ARG IMAGE_DIGEST=sha256:b9cc19c4f422bd75cfcbef7b6ea563270629da3fd8652c4f9ec94217ce1a9693

FROM ${IMAGE}@${IMAGE_DIGEST} AS compile-image

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

VOLUME [ "/scripts", "/settings" ]

WORKDIR /settings

COPY ./requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir --user


## Runtime image
FROM ${IMAGE}@${IMAGE_DIGEST} AS runtime-image

RUN apk add --no-cache bash \
                       python3-dev

WORKDIR /settings

COPY --from=compile-image /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY ./entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/bin/sh", "./entrypoint.sh"]
