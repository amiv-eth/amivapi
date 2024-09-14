FROM python:3.12-alpine

# Create user with home directory and no password and change workdir
RUN adduser -Dh /api amivapi
WORKDIR /api
# API will run on port 80
EXPOSE 8080
# Environment variable for default config file location
ENV AMIVAPI_CONFIG=/api/config.py

# Install bjoern and dependencies for install
RUN apk add --no-cache --virtual .deps \
    musl-dev gcc git && \
    # Keep libev for running bjoern, libjpeg and zlib for Pillow
    apk add --no-cache libev-dev zlib-dev jpeg-dev && \
    pip install bjoern

# Copy files to /api directory, install requirements.
COPY amivapi /api/amivapi
COPY requirements.txt /api/
COPY setup.py /api/
COPY LICENSE /api/
COPY AUTHORS /api/
COPY MANIFEST.in /api/
COPY tox.ini /api/
RUN pip install -r /api/requirements.txt

# Install amivapi to enable CLI commands
# The -e flag installs links only instead of moving files to /usr/lib
RUN pip install -e /api/.

# Cleanup dependencies
RUN apk del .deps

# Switch user
USER amivapi

# Start bjoern as default
CMD ["amivapi", "run", "prod"]
