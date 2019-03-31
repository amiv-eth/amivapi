#!/bin/bash

docker build -t amivapi-testrunner -f Dockerfile.test . || exit 1
docker run --rm -it --name testrunner --mount type=tmpfs,destination=/tmp \
    amivapi-testrunner $@
