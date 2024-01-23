
ARG IMAGE=python:3.11-slim-bookworm
ARG IMAGE_DIGEST=sha256:d11b9bd5e49ea7401753d78f4d3b56f3aec952b85b49bcae88981f0452818e0b

# Compile Image
FROM ${IMAGE}@${IMAGE_DIGEST} AS compile-image

WORKDIR /opt/scheduler

# Install pip Packages
COPY ["app/requirements.txt", "/opt/scheduler/requirements.txt"]
RUN pip3 install -r /opt/scheduler/requirements.txt --user


# Runtime Image
FROM ${IMAGE}@${IMAGE_DIGEST} AS runtime-image

# System update and package installation
RUN apt-get update --fix-missing && \
    apt-get autoremove -y && \
    apt-get clean && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get install -y tzdata nginx default-mysql-client procps

# Copy pip packages and set PATH
COPY --from=compile-image /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Nginx Setup
COPY ["nginx/nginx.conf", "/etc/nginx/nginx.conf"]
COPY ["nginx/scheduler.conf", "/etc/nginx/conf.d/scheduler.conf"]
RUN rm -r /etc/nginx/sites-enabled /etc/nginx/sites-available

# Scheduler App Setup
WORKDIR /opt/scheduler
COPY ["app/", "/opt/scheduler/"]
COPY ["version", "/opt/scheduler/version"]
RUN mkdir -p /opt/scheduler/logs
RUN pip3 install -r /opt/scheduler/requirements.txt --user

# Tini Setup
ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini
ENTRYPOINT ["/tini", "--"]

CMD ["/opt/scheduler/entrypoint.sh"]
