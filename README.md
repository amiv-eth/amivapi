# amivapi

[![Build status](https://secure.travis-ci.org/amiv-eth/amivapi.png?branch=master)](https://secure.travis-ci.org/amiv-eth/amivapi)
[![Coverage Status](https://coveralls.io/repos/amiv-eth/amivapi/badge.svg)](https://coveralls.io/r/amiv-eth/amivapi)

AMIV API is a Python-EVE based REST interface to manage members, events, mail forwards, job offers and study documents for a student organisation. It was created by AMIV an der ETH to restructure the existing IT infrastructure. If you are not from AMIV and think this is useful feel free to fork and modify.

[Request Cheatsheet (Filtering etc.)](docs/Cheatsheet.md)

[Python EVE Documentation](http://python-eve.org/features.html)

[How to use central OAuth2 login](docs/OAuth.md)


## Installation & Prerequisites

### Docker

AMIV API is available as a [Docker](https://www.docker.com) container with the
name [amiveth/amivapi](https://hub.docker.com/r/amiveth/amivapi/).

You only need to install Docker, nothing else is required.

### Manual Installation for Development

For development, we recommend to clone the repository and install AMIV API
manually.

First of all, we advice using a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

If your virtual environment is ready, clone and install AMIV API:

```sh
git clone https://github.com/amiv-eth/amivapi.git
cd amivapi
pip install -r requirements.txt
```

This will also install the `amivapi` command, which you can use to start
a development server (more below).

### MongoDB

Regardless of your type of installation, AMIV API requires
[MongoDB](https://docs.mongodb.com). If you have the connection data to your
database, you are good to go and can skip this section.

If you need to set up a local database for testing or development, you
can either use the following guides to get it 
[installed](https://docs.mongodb.com/manual/installation/) and
[running](https://docs.mongodb.com/manual/tutorial/manage-mongodb-processes/)
or you can use Docker as well.

The following command runs a MongoDB service available on the default port
(27017), preconfigured with a database `amivapi` with user `amivapi` and
password `amivapi`.

```sh
# Create a network s.t. the api service can later be connected to the db
docker network create --driver overlay backend
docker service create \
    --name mongodb -p 27017:27017 --network backend\
    -e MONGODB_DATABASE=amivapi \
    -e MONGODB_USERNAME=amivapi \
    -e MONGODB_PASSWORD=amivapi \
    bitnami/mongodb
```

If you have a local MongoDB running, the following command might be useful
to set up database and user quickly:

```sh
mongo amivapi --eval \
'db.createUser({user:"amivapi",pwd:"amivapi",roles:["readWrite"]});'
```

## Configure and Start AMIV API

### Configuration File

Now it's time to configure AMIVAPI. Create a file `config.py`
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

# LDAP connection (special LDAP user required, *not* nethz username & password)
# LDAP_USERNAME = ''
# LDAP_PASSWORD = ''
```

(These are only the most imporant settings. The config file overwrites
the default settings, so any value defined in
[settings.py](amivapi/settings.py) can be changed if needed.)

### Run using Docker

Configuration files can be used for services easily using
[Docker configs](https://docs.docker.com/engine/swarm/configs/):

```sh
docker config create amivapi_config config.py
```

Now start the API service (make sure to put it in the same network as MongoDB
if you are running a MongoDB service locally).

```sh
# Webserver Mode
# Map port 80 (host) to 8080 (container)
docker service create \
    --name amivapi  -p 80:8080 --network backend \
    --config source=amivapi_config,target=/api/config.py \
    amiveth/amivapi

# The command `amivapi cron --continuous` starts the container in alternative mode:
# It will not run a webserver, but execute scheduled tasks periodically.
docker service create \
    --name amivapi-cron --network backend \
    --config source=amivapi_config,target=/api/config.py \
    amiveth/amivapi amivapi cron --continuous
```

(If you want to mount the config somewhere else, you can use the environment
variable `AMIVAPI_CONFIG` to specify the config path in the container.)

### Run locally

If you have installed AMIV API locally, you can use the CLI to start it:

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

First, create a test user `test_user` with password `test_pw` in the `test_amviapi` database, which will be used for all tests. You only need
to do this once to prepare the database.

```sh
mongo test_amivapi --eval \
'db.createUser({user:"test_user",pwd:"test_pw",roles:["readWrite"]});'
```

Install the test requirements:

```sh
pip install tox
```

Now you can run all tests using tox

```sh
# Run everything
tox

# Select only a single python version
tox -e py36

# Filter tests by name
tox -- -k <keyword>

# Combining both is possible too
tox -e py36 -- -k <keyword>
```

### Integration Tests

The integration tests for ssh mailing list creation and LDAP require additional
information to be run, which should not be published.
Therefore, these tests are automatically *skipped* (as you can see in the tox
summary), unless the relevant information is provided with environment
variables.

#### SSH

Set the following environment variables:

- `SSH_TEST_ADDRESS`, e.g. `user@remote.host`
- `SSH_TEST_KEYFILE`(optional): file containing a key that
  is authorized to access the server 
- `SSH_TEST_DIRECTORY`(optional): Directory on remote server where test files
  are stored. Uses  `/tmp/amivapi-test/` by default

#### LDAP

- `LDAP_TEST_USERNAME` and `LDAP_TEST_PASSWORD`
  (*not* your nethz, special LDAP account required)
- `LDAP_TEST_USER_NETHZ` (required to test user import)
  The test will return the imported user data, be sure to verify it
- `LDAP_TEST_USER_PASSWORD` (required to test user login)

Additionally, you need to be inside the ETH network, e.g. using a VPN, otherwise the ETH LDAP server can't be reached. Furthermore be patient,
as the LDAP tests take a little time to complete.

## Problems or Questions?

For any comments, bugs, feature requests please use the issue tracker, don't hasitate to create issues, if we don't like your idea we are not offended.

If you need help deploying the API or creating a client, feel free to message us at api@amiv.ethz.ch
