#amivapi

[![Build status](https://secure.travis-ci.org/amiv-eth/amivapi.png?branch=master)](https://secure.travis-ci.org/amiv-eth/amivapi)
[![Coverage Status](https://coveralls.io/repos/amiv-eth/amivapi/badge.svg)](https://coveralls.io/r/amiv-eth/amivapi)

AMIV API is a Python-EVE based REST interface to manage members, events, mail forwards, job offers and study documents for a student organisation. It was created by AMIV an der ETH to restructure the existing IT infrastructure. If you are not from AMIV and think this is useful feel free to fork and modify.

## Quickstart

### Prerequisites

You need to have mongodb [installed](https://docs.mongodb.com/manual/installation/) and [running](https://docs.mongodb.com/manual/tutorial/manage-mongodb-processes/).

You should also use a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

### Installation

    git clone -b mongo https://github.com/amiv-eth/amivapi.git amivapi
    cd amivapi
    pip install -r requirements.txt

This will also install amivapi in editable mode (take a look at 
`requirements.txt` if you are curious) which will allow us to use the command
line interface of amivapi.

### Setup

First you need a config file:

    amivapi create_config

Now you are basically done, if you want to start a development server just type

    amivapi run

### Production

If you want to use amivapi properly behind a webserver, e.g. Apache or Nginx
with uwsgi, you need to create a file, e.g. `app.py`, with the following content:

    from amivapi import create_app

    app = create_app()

### Note on filepaths

`create_app()` as well as `amivapi run` will look for a config file in the
current working directory. In production, you need to use the appropriate
settings, e.g. `chdir` in uwsgi.
Another way is to just pass the absolute path to your config file as argument
for `create_app()`

    app = create_app("/path/to/your/config")

For `amivapi run` you can also specify a config, see `amivapi run --help`.

## Running The Tests

Install the test requirements:

    pip install pytest tox

To run all tests:

    tox

To run tests based on a keyword:

    tox -- -k <keyword>

To run just one python version:

    tox -e py36

## Further Information

For information about using the API as a client have a look at docs/User_Guide.md.

If you want to develop continue with the Developer Guide.

Be aware! Currently parts of the documentation may be outdated.

## Problems or Questions?

For any comments, bugs, feature requests please use the issue tracker, don't hasitate to create issues, if we don't like your idea we are not offended.

If you need help deploying the API or creating a client, feel free to message us at api@amiv.ethz.ch
