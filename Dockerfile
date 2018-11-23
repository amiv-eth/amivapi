FROM python:3.6-alpine

# Create user with home directory and no password and change workdir
RUN adduser -Dh /api amivapi
WORKDIR /api
# API will run on port 80
EXPOSE 8080
# Environment variable for default config file location
ENV AMIVAPI_CONFIG=/api/config.py

# Install bjoern and dependencies for install
RUN apk add --no-cache --virtual .deps \
        musl-dev python-dev gcc git && \
    # Keep libev for running bjoern, libjpeg and zlib for Pillow
    apk add --no-cache libev-dev zlib-dev jpeg-dev && \
    pip install bjoern

# Copy files to /api directory, install requirements
COPY ./ /api
RUN pip install -r /api/requirements.txt

# Install amivapi to enable CLI commands
RUN pip install /api

# Cleanup dependencies
RUN apk del .deps

# Switch user
USER amivapi

# Start bjoern as default
CMD ["amivapi", "run", "prod"]
