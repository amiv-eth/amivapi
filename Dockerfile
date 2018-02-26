FROM python:3.6-alpine

# Create user with home directory and no password
RUN adduser -Dh /api amivapi
# API will run on port 80
EXPOSE 80
# Files will be in /api directory
WORKDIR /api
# Environment variable for config, use path for docker secrets as default
ENV AMIVAPI_CONFIG=/run/secrets/amivapi_config

# Install uwsgi (build tools are required), git is required for install later
# This would be easier with th uwsgi-python3 packet, but it's somehow not found
RUN apk add --no-cache --virtual .uwsgi-deps \
        python3-dev build-base linux-headers &&\
    apk add --no-cache --virtual .requirements-deps git &&\
    # We need to keep pcre-dev, otherwise uwsgi won't start
    apk add --no-cache pcre-dev && \
    pip install uwsgi

# Copy essential files  to /api directory, install requirements
COPY ./amivapi /api/amivapi
COPY ./requirements.txt /api/requirements.txt
COPY ./setup.py /api/setup.py
COPY ./LICENSE /api/LICENSE
RUN pip install -r /api/requirements.txt

# Cleanup dependencies
RUN apk del .uwsgi-deps .requirements-deps

# Create a minimal python file that creates an amivapi app
RUN printf 'from amivapi import create_app\napp = create_app()' > /api/app.py


# Run uwsgi as user amivapi to serve the app on port 80
CMD ["uwsgi", "--master", \
# Switch user
"--uid", "amivapi", "--gid", "amivapi", \
# [::] is required to listen for both IPv4 and IPv6
# 80 is a priviledged port, using 'shared-port' binds before switching user
# '=0' references the first shared port
"--shared-socket", "[::]:80", \
"--http", "=0", \
# More efficient usage of resources
"--processes", "4", \
# Exit if app cannot be started, e.g. if config is missing
"--need-app", \
# Allow accessing the app at / as well as /amivapi for flexible hosting
"--manage-script-name", \
"--mount", "/amivapi=app:app"]
