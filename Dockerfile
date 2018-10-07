FROM python:3.6-alpine

# Create user with home directory and no password and change workdir
RUN adduser -Dh /api amivapi
WORKDIR /api
# API will run on port 80
EXPOSE 8080
# Environment variable for config
ENV AMIVAPI_CONFIG=/api/config.py

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

# Start bjoern as default
CMD ["amivapi", "run", "prod"]
