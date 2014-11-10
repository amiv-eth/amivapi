import codecs
import datetime as dt
from os import mkdir
from os.path import abspath, dirname, join, exists, expanduser
import random
import string

from flask import Flask
from flask.ext.script import (
    Manager,
    prompt,
    prompt_bool,
    prompt_choices,
    prompt_pass,
)

from amivapi import settings


# Using a "fake" flask app, since the create_config command is usually used to
# create a dev-config, which would already be required by the real Flask app
# to load properly
manager = Manager(Flask("amivapi"))


def make_config(name, **config):
    config_dir = dirname(name)
    if not exists(config_dir):
        mkdir(config_dir, 0700)

    with codecs.open(name, "w", encoding="utf-8") as f:
        f.write('"""Automatically generated on %s"""\n\n'
                % dt.datetime.utcnow())

        for key, value in sorted(config.items()):
            f.write("%s = %r\n" % (key.upper(), value))


@manager.command
def create_config():
    """Creates a new configuration for an environment.

    The config file is stored in the ROOT/config directory.
    """
    environment = prompt_choices("Choose the environment the config is for",
                                 ["development", "testing", "production"],
                                 default="development")

    target_file = join(settings.ROOT_DIR, "config", "%s.cfg" % environment)
    if exists(target_file):
        if not prompt_bool("The file config/%s.cfg already exists, "
                           "do you want to overwrite it?" % environment):
            return

    # Configuration values
    config = {
        'SECRET_KEY': "".join(
            random.choice(string.ascii_letters + string.digits)
            for _ in range(32)
        ),
        'DEBUG': environment == "development",
        'TESTING': environment == "testing",
    }

    # Ask for database settings
    db_uri = None
    db_type = prompt_choices("Choose the type of database",
                             ["sqlite", "mysql"],
                             default="sqlite")
    if db_type == "sqlite":
        db_filepath = prompt("Path to db file (including filename)",
                             default=join(settings.ROOT_DIR, "data.db"))
        db_uri = "sqlite:///%s" % abspath(expanduser(db_filepath))

    elif db_type == "mysql":
        user = prompt("MySQL username", default="amivapi")
        pw = prompt_pass("MySQL password")
        host = prompt("MySQL host", default="localhost")
        db = prompt("MySQL database", default="amivapi")

        db_uri = "mysql://%s:%s@%s/%s?charset=utf8" % (user, pw, host, db)

    config['SQLALCHEMY_DATABASE_URI'] = db_uri

    # Write everything to file
    # Note: The file is opened in non-binary mode, because we want python to
    # auto-convert newline characters to the underlying platform.
    make_config(target_file, **config)


if __name__ == "__main__":
    manager.run()
