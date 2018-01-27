# amivapi

[![Build status](https://secure.travis-ci.org/amiv-eth/amivapi.png?branch=master)](https://secure.travis-ci.org/amiv-eth/amivapi)
[![Coverage Status](https://coveralls.io/repos/amiv-eth/amivapi/badge.svg)](https://coveralls.io/r/amiv-eth/amivapi)

AMIV API is a Python-EVE based REST interface to manage members, events, mail forwards, job offers and study documents for a student organisation. It was created by AMIV an der ETH to restructure the existing IT infrastructure. If you are not from AMIV and think this is useful feel free to fork and modify.


## Installation

You need to have mongodb [installed](https://docs.mongodb.com/manual/installation/) and [running](https://docs.mongodb.com/manual/tutorial/manage-mongodb-processes/).

You should also use a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Clone and install AMIV API:

    git clone -b mongo https://github.com/amiv-eth/amivapi.git amivapi
    cd amivapi
    pip install -r requirements.txt

This will also install amivapi in editable mode (take a look at
`requirements.txt` if you are curious) which allows us to use the command
line interface of amivapi:

    # Run a development server
    amivapi run
    # Get help, works for sub-commands as well
    amivapi --help
    amivapi run --help


## Running in Production

If you want to use AMIV API properly behind a webserver, e.g. Apache or Nginx
with uwsgi, you need to create a file, e.g. `app.py`, with the following content:

    from amivapi import create_app

    app = create_app()


## Configuration

Now it's time to configure AMIVAPI. Create a file `config.py`
(you can choose any other name as well) with the following content:

    # Root password, *definitely* change this!
    ROOT_PASSWORD = 'root'

    # MongoDB Configuration
    MONGO_HOST = 'localhost'
    MONGO_PORT = 27017
    MONGO_DBNAME = 'amivapi'
    MONGO_USERNAME = ''
    MONGO_PASSWORD = ''

    # Mailing lists for groups (optional, uncomment if needed)
    # MAILING_LIST_DIR = '/directory/to/store/mailing/list/files/'

    # SMTP configuration for mails sent by AMIVAPI (optional)
    # API_MAIL = 'api@amiv.ethz.ch'
    # SMTP_SERVER = 'localhost'
    # SMTP_PORT = '587'
    # SMTP_USERNAME = ''
    # SMTP_PASSWORD = ''

AMIV API looks for a configuration in the following order:

1. If using `create_app`, you can name the file explicitly:

    app = create_app(config_file="/path/to/your/config.py")

2. If no file is specified, you can use the `AMIVAPI_CONFIG` environment
   variable:

    $set AMIVAPI_CONFIG path/to/your/config.py

3. If no environment variable is specified either, AMIV API checks for a file
   name `config.py` in the current working directory

For `amivapi run` and all other `amivapi` commands you can also specify a
config, see `amivapi <command> --help`, e.g. `amivapi run --help`


## Running The Tests

Install the test requirements:

    pip install pytest tox

To run all tests:

    tox

To run tests based on a keyword:

    tox -- -k <keyword>

To run just one python version:

    tox -e py36


## Problems or Questions?

For any comments, bugs, feature requests please use the issue tracker, don't hasitate to create issues, if we don't like your idea we are not offended.

If you need help deploying the API or creating a client, feel free to message us at api@amiv.ethz.ch
