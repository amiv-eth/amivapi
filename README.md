# amivapi

[![Build status](https://secure.travis-ci.org/amiv-eth/amivapi.png?branch=master)](https://secure.travis-ci.org/amiv-eth/amivapi)
[![Coverage Status](https://coveralls.io/repos/amiv-eth/amivapi/badge.svg)](https://coveralls.io/r/amiv-eth/amivapi)

AMIV API is a Python-EVE based REST interface to manage members, events, mail forwards, job offers and study documents for a student organisation. It was created by AMIV an der ETH to restructure the existing IT infrastructure. If you are not from AMIV and think this is useful feel free to fork and modify.

[Request Cheatsheet (Filtering etc.)](docs/Cheatsheet.md)
[Python EVE Documentation](http://python-eve.org/features.html)

[How to use central login](docs/OAuth.md)

## Deploy using Docker

AMIV API is available as a [docker](https://www.docker.com) container.
If you do not have mongodb, you can also use docker to quickly start
a database with the default settings used by AMIV API:

```sh
# Create a network s.t. database and api can communicate
docker network create --driver overlay backend
docker service create \
    --name mongodb -p 27017:27017 --network backend\
    -e MONGODB_DATABASE=amivapi \
    -e MONGODB_USERNAME=amivapi \
    -e MONGODB_PASSWORD=amivapi \
    bitnami/mongodb
```

Next, create a configuration with (at least) the mongodb credentials and save
it as `amivapi_config.py` (or choose another name).

```python
MONGO_HOST = 'mongodb'  # Use the name of your mongodb service
MONGO_PORT = 27017
MONGO_DBNAME = 'amivapi'
MONGO_USERNAME = 'amivapi'
MONGO_PASSWORD = 'amivapi'
```

Finally, create API service and give it access to the config using a docker
secret:

```sh
# Create secret
docker secret create amivapi_config <path/to/amivapi_config.py>

# Create new API service with secret
# Map port 80 (host) to 8080 (container)
docker service create \
    --name amivapi  -p 80:8080 --network backend \
    --secret amivapi_config \
    amiveth/amivapi
```

If you want to use a different name for the secret (or cannot use secrets
and have to mount the config manually), you can use the environment
variable `AMIVAPI_CONFIG` to set the config path in the API container.

## Installation

You need to have mongodb [installed](https://docs.mongodb.com/manual/installation/) and [running](https://docs.mongodb.com/manual/tutorial/manage-mongodb-processes/).

You should also use a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Clone and install AMIV API:

```sh
git clone https://github.com/amiv-eth/amivapi.git
cd amivapi
pip install -r requirements.txt
```

This will also install amivapi in editable mode (take a look at
`requirements.txt` if you are curious) which allows us to use the command
line interface of amivapi:

```sh
# Run a development server
amivapi run
# Get help, works for sub-commands as well
amivapi --help
amivapi run --help
```

## Running in Production

If you want to use AMIV API properly behind a webserver, e.g. Apache or Nginx
with uwsgi, you need to create a file, e.g. `app.py`, with the following content:

```python
from amivapi import create_app

app = create_app()
```

## Configuration

Now it's time to configure AMIVAPI. Create a file `config.py`
(you can choose any other name as well) with the following content:

```python
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
    
# Remote mailings list files via ssh (optional)
# REMOTE_MAILING_LIST_ADDRESS = 'user@remote.host'
# REMOTE_MAILING_LIST_KEYFILE = ''
# REMOTE_MAILING_LIST_DIR = './'

# SMTP configuration for mails sent by AMIVAPI (optional)
# API_MAIL = 'api@amiv.ethz.ch'
# SMTP_SERVER = 'localhost'
# SMTP_PORT = '587'
# SMTP_USERNAME = ''
# SMTP_PASSWORD = ''
```

AMIV API looks for a configuration in the following order:

1. If using `create_app`, you can name the file explicitly:

   ```python 
   app = create_app(config_file="/path/to/your/config.py")
   ```

2. If no file is specified, you can use the `AMIVAPI_CONFIG` environment
   variable:

   ```sh
   $set AMIVAPI_CONFIG path/to/your/config.py
   ```

3. If no environment variable is specified either, AMIV API checks for a file
   name `config.py` in the current working directory

For `amivapi run` and all other `amivapi` commands you can also specify a
config, see `amivapi <command> --help`, e.g. `amivapi run --help`


## Running The Tests

Create a test user `test_user` with password `test_pw` in the `test_amviapi`
database, which will be used for all tests.

```sh
mongo test_amivapi --eval \
'db.createUser({user:"test_user",pwd:"test_pw",roles:["readWrite"]});'
```

Install the test requirements:

```sh
pip install pytest tox
```
To run all tests:

```sh
tox
```

To run tests based on a keyword:

```sh
tox -- -k <keyword>
```

To run just one python version:

```sh
tox -e py36
```

## Problems or Questions?

For any comments, bugs, feature requests please use the issue tracker, don't hasitate to create issues, if we don't like your idea we are not offended.

If you need help deploying the API or creating a client, feel free to message us at api@amiv.ethz.ch
