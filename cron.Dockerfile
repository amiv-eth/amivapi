FROM python:3.6-alpine

# Create user with home directory and no password and change workdir
WORKDIR /api
# Environment variable for config, use path for docker secrets as default
ENV AMIVAPI_CONFIG=/run/secrets/amivapi_config

# Install bjoern and dependencies for install (we need to keep libev)
RUN apk add --no-cache --virtual .deps \
        musl-dev python-dev gcc git

# Copy files to /api directory, install requirements
COPY ./ /api
RUN pip install -r /api/requirements.txt

# Cleanup dependencies
RUN apk del .deps

# Build entrypoint script
RUN echo "#!/bin/sh" >> /entrypoint.sh && \
    echo "echo \"\$CRON_TIME python3 /api/amivapi/cron.py\" >> /crontab.txt" >> /entrypoint.sh && \
    echo "cron -f /crontab.txt" >> /entrypoint.sh

# Default configuration
ENV CRON_TIME="39 3 * * *"

CMD ["/bin/sh", "entrypoint.sh"]
