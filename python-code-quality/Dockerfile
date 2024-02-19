FROM python:3.11-slim-bookworm AS compile-image

# Installation of the pip packages
WORKDIR /app
COPY [ "." , "/app/"]

# Install packages and generate a frozen requirements file if it doesn't exist
RUN if [ -f requirements_frozen.txt ]; then \
        pip install --no-cache-dir -r requirements_frozen.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt && \
        pip freeze > requirements_frozen.txt; \
    fi
