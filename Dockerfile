FROM python:3.6-alpine

# Create user with home directory and no password and change workdir
RUN adduser -Dh /api amivapi
WORKDIR /api
# API will run on port 80
EXPOSE 8080
# Environment variable for config, use path for docker secrets as default
ENV AMIVAPI_CONFIG=/run/secrets/amivapi_config

# Install bjoern and dependencies for install
RUN apk add --no-cache --virtual .deps \
        musl-dev python-dev gcc git && \
    # Keep libev for running bjoern
    apk add --no-cache libev-dev && \
    pip install bjoern

# Copy files to /api directory, install requirements
COPY ./ /api
RUN pip install -r /api/requirements.txt

# Cleanup dependencies
RUN apk del .deps

# Switch user
USER amivapi

# Default configuration for cron
ENV CRON_TIME="39 3 * * *"

# Start bjoern as default
CMD ["./start_server"]
