FROM docker:cli AS compile-image

# bash (convenience) and linux-headers (uswgi build dependency) added
# build-essentials to build-base, python3-pip to py3-pip
RUN apk add --no-cache unzip \
                       python3-dev \
                       py3-pip \
                       linux-headers \
                       gcc \
                       build-base

WORKDIR /opt/seatable-python-starter

COPY ["./", "/shared/seatable-python-starter/"]

RUN pip install -r /shared/seatable-python-starter/requirements.txt --user \
    && chmod +x /shared/seatable-python-starter/entrypoint.sh


## Runtime image
FROM docker:cli AS runtime-image

RUN apk add --no-cache bash \
                       curl \
                       python3-dev

WORKDIR /opt/seatable-python-starter

COPY ["./", "/shared/seatable-python-starter/"]
COPY --from=compile-image /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

ENTRYPOINT ["/shared/seatable-python-starter/entrypoint.sh"]
