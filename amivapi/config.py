from os.path import abspath, dirname, join


ROOT_PATH = abspath(join(dirname(__file__), ".."))

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


# Database settings

SQLALCHEMY_DATABASE_URI = "sqlite:///%s/data.db" % ROOT_PATH
SQLALCHEMY_ECHO = True


# Performance settings

BANDWIDTH_SAVER = False
XML = False


# Security

# This is used to sign login tokens, changing it will log out all users
# CHANGE AT INSTALLATION TO SOME GOOD RANDOM STRING(AT LEAST 32 CHARACTERS)
LOGIN_SECRET = 'dev_secret'

# Time until a login token becomes invalid
LOGIN_TIMEOUT = 60*60*24*31
