# amivapi

[![Build status](https://secure.travis-ci.org/amiv-eth/amivapi.png?branch=master)](https://secure.travis-ci.org/amiv-eth/amivapi)
[![Coverage Status](https://coveralls.io/repos/amiv-eth/amivapi/badge.svg)](https://coveralls.io/r/amiv-eth/amivapi)

AMIV API is a [Python-EVE]((http://docs.python-eve.org)) based REST interface
to manage members, events, mail forwards, job offers and study documents for a
student organisation. It was created by [AMIV an der ETH](http://amiv.ethz.ch) to restructure the
existing IT infrastructure. If you are not from AMIV and think this is useful,
feel free to fork and modify.

If you only want to use AMIV API, check out the online documentation
(There's a link in the github description above).

If you are an administrator and wish to get the AMIV API running, keep reading!

If you are a developer looking to work on AMIV API, it's best to look at the
code directly. You can start with [bootstrap.py](amivapi/bootstrap.py),
where all modules are assembled into a single app object. From there on,
check out the different sub-modules. Each resource is defined in a dedicated
sub-directory, some smaller functionality are defined in a single file.

You do not need to install and configure AMIV API to test it. You can skip
the installation and configuration sections and head right to the bottom
of the README, where testing is explained.


## Installation & Prerequisites


### Docker

AMIV API is available as a [Docker](https://www.docker.com) container with the
name [amiveth/amivapi](https://hub.docker.com/r/amiveth/amivapi/).

You only need to install Docker, nothing else is required to run the api.
However, a [MongoDB](https://docs.mongodb.com) database is required to store data.
See [below](#Configure and Start AMIV API) for instructions to configure the database connection and other properties.


### Development Setup

For development, we provide a easy-to-use docker setup which sets up local AMIV API and MongoDB instances via [Docker Compose](https://docs.docker.com/compose/).

Clone this repository, [install Docker Compose](https://docs.docker.com/compose/install/), and run:

```sh
docker-compose up -d
```

This will start a MongoDB and an API container. You can stop them using:

```sh
docker-compose stop
```

The `amivapi/` directory is mounted inside the API containers.
This means that you do *not* have to re-run docker compose after changing the code.
The dev server inside the container will detect changes and restart automatically.

*Important*: The MongoDB is hosted *in-memory* only to speed up testing.
The development environment is not meant for persistent data.


### Manual installation

Instead of using docker, you can install the api manually.

First of all, we advise using a [virtual environment](https://docs.python.org/3/tutorial/venv.html).
If your virtual environment is ready, install all requirements as well as the api itself, which gives you acces to the CLI.

```sh
pip install -r requirements.txt
# Install amivapi in `editable mode` to get the `amivapi` command
pip install -e .
```


## Configure and Start AMIV API

### Configuration File

Now it's time to configure AMIV API. Create a file `config.py`
(you can choose any other name as well) with the following content:


```python
# Root password, *definitely* change this!
ROOT_PASSWORD = 'root'

# MongoDB Configuration
MONGO_HOST = 'mongodb'
MONGO_PORT = 27017
MONGO_DBNAME = 'amivapi'
MONGO_USERNAME = 'amivapi'
MONGO_PASSWORD = 'amivapi'

# Sentry error logging
# SENTRY_DSN = "https://<key>@sentry.io/<project>"
# SENTRY_ENVIRONMENT = 'production'

# Mailing lists for groups (optional, uncomment if needed)
# MAILING_LIST_DIR = '/directory/to/store/mailing/list/files/'

# Remote mailings list files via ssh (optional)
# REMOTE_MAILING_LIST_ADDRESS = 'user@remote.host'
# REMOTE_MAILING_LIST_KEYFILE = ''
# REMOTE_MAILING_LIST_DIR = './'

# SMTP configuration for mails sent by AMIVAPI (optional)
# SMTP_SERVER = 'localhost'
# SMTP_PORT = '587'
# SMTP_USERNAME = ''
# SMTP_PASSWORD = ''

# Mail configuration (`{subject}` is a placeholder, filled by the API)
# API_MAIL = 'api@amiv.ethz.ch'
# API_MAIL_SUBJECT = '[AMIV] {subject}'

# Allow accessing a list of newsletter subscribers at /newslettersubscribers
# SUBSCRIBER_LIST_USERNAME = ''
# SUBSCRIBER_LIST_PASSWORD = ''

# LDAP connection (special LDAP user required, *not* nethz username & password)
# LDAP_USERNAME = ''
# LDAP_PASSWORD = ''
```

(These are only the most important settings. The config file overwrites
the default settings, so any value defined in
[settings.py](amivapi/settings.py) can be changed if needed.)

### Configuration File Location

The official AMIV API docker container expects the config file at `/api/config.py`.
If you want to mount the config somewhere else, you can use the environment
variable `AMIVAPI_CONFIG` to specify the config path in the container.


### Development using Docker

The development container is pre-configured to use the configuration found in [`dev_config.py`](dev_config.py).
Adjust the settings as needed, but do not change the MongoDB config.

You need to manually restart the containers after configuration changes.

As long as the container is running, the API is available under `localhost:5000`.

You can also access the API CLI inside the docker container.

```sh
# Run the `amivapi` command inside the `api` container.
docker-compose exec api amivapi

# See all options:
docker-compose exec api amivapi --help
```


### Manual Configuration

If you have installed AMIV API manually, you can use the CLI to start it, optionally specifying a config file.

```sh
# Start development server
amivapi run dev

# Start production server (requires the `bjoern` package)
amivapi run prod

# Execute scheduled tasks periodically
amivapi cron --continuous

# Specify config if its not `config.py` in the current directory
amivapi --config <path> run dev

# Get help, works for sub-commands as well
amivapi --help
amivapi run --help
```


## For Developers: Running The Tests

### Option 1: With Docker

You can easily run the tests with the provided Docker environment.

```sh
# Start the containers, if they are not running already.
docker-compose up -d

# Run pytest.
docker-compose exec api pytest

# Run specific directories/files only. See pytest docs for more!
docker-compose exec api pytest amivapi/tests/users
docker-compose exec api pytest amivapi/tests/users/test_users.py
docker-compose exec api pytest -k test_user
```

TODO: Tox not yet working!


### Integration Tests

The integration tests for ssh mailing list creation and LDAP require additional
information to be run, which should not be published.
Therefore, these tests are automatically *skipped* (as you can see in the tox
summary), unless the relevant information is provided with environment
variables.

You need to update `docker-compose.yml` and add the respective environment variables to enable these tests.

#### SSH

Set the following environment variables:

- `SSH_TEST_ADDRESS`, e.g. `user@remote.host`
- `SSH_TEST_KEYFILE`(optional): file containing a key that
 is authorized to access the server
- `SSH_TEST_DIRECTORY`(optional): Directory on remote server where test files
 are stored. Uses `/tmp/amivapi-test/` by default

#### LDAP

- `LDAP_TEST_USERNAME` and `LDAP_TEST_PASSWORD`
 (*not* your nethz, special LDAP account required)
- `LDAP_TEST_USER_NETHZ` (required to test user import)
 The test will return the imported user data, be sure to verify it
- `LDAP_TEST_USER_PASSWORD` (required to test user login)

Additionally, you need to be inside the ETH network, e.g. using a VPN, otherwise the ETH LDAP server can't be reached.
Furthermore be patient, as the LDAP tests take a little time to complete.

#### Sentry

- `SENTRY_TEST_DSN`

The test will use the `testing` environment.

## Problems or Questions?

For any comments, bugs, feature requests: please use the issue tracker and don't hasitate to create issues. If we don't like your idea, we will not feel offended.

If you need help deploying the API or creating a client, feel free to message us at [api@amiv.ethz.ch](mailto:api@amiv.ethz.ch) .
