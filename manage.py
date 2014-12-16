import codecs
import datetime as dt
from os import mkdir
from os.path import abspath, dirname, join, exists, expanduser
import rsa

from sqlalchemy.exc import OperationalError

from flask import Flask
from eve import Eve
from flask.ext.script import (
    Manager,
    prompt,
    prompt_bool,
    prompt_choices,
    prompt_pass,
)

from amivapi import settings, bootstrap
from amivapi.models import User
from amivapi.auth import create_new_hash
from amivapi.utils import init_database


def real_or_dummy_app(config=None):
    if config:
        return bootstrap.create_app(config)

    # When no config is given, us a fake flask app, so that commands which do
    # not require a real app instance still work.
    return Flask("amivapi")


manager = Manager(real_or_dummy_app)
manager.add_option("-c", "--config", dest="config", required=False)


def make_config(name, **config):
    config_dir = dirname(name)
    if not exists(config_dir):
        mkdir(config_dir, 0700)

    with codecs.open(name, "w", encoding="utf-8") as f:
        f.write('"""Automatically generated on %s"""\n\n'
                % dt.datetime.utcnow())

        for key, value in sorted(config.items()):
            f.write("%s = %r\n" % (key.upper(), value))


# Create public/private keys to sign login tokens
def create_key_files(environment):
    print("Creating public/private key pair. This may take a while...")

    public_key_file = join(settings.ROOT_DIR, "config",
                           "%s-login-private.pem" % environment)
    private_key_file = join(settings.ROOT_DIR, "config",
                            "%s-login-public.pem" % environment)
    (private_key, public_key) = rsa.newkeys(2048)

    with codecs.open(public_key_file, "w", encoding="utf-8") as f:
        f.write(public_key.save_pkcs1(format='PEM'))

    with codecs.open(private_key_file, "w", encoding="utf-8") as f:
        f.write(private_key.save_pkcs1(format='PEM'))


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

    config['ROOT_MAIL'] = prompt("Maintainer E-Mail")

    # Write everything to file
    # Note: The file is opened in non-binary mode, because we want python to
    # auto-convert newline characters to the underlying platform.
    make_config(target_file, **config)

    create_key_files(environment)

    d = config['STORAGE_DIR']
    if not exists(d):
        mkdir(d)

    print("Run manage.py create_database to create a database!")


@manager.command
def create_database():
    """ Creates the database, a root user and an anonymous user """

    if not isinstance(manager.app, Eve):
        print("Please specify an environment with -c")
        exit(0)

    # FIXME(Conrad): This should actually provide a connection, not an engine
    init_database(manager.app.data.driver.engine, manager.app.config)


@manager.command
def set_root_password():
    """Sets the root password. """

    if not isinstance(manager.app, Eve):
        print("Please specify an environment with -c")
        exit(0)

    session = manager.app.data.driver.session

    try:
        root = session.query(User).filter(User.id == 0).one()
    except OperationalError:
        print ("No root user found, please create the database using " +
               "`python manage.py create_database`")
        exit(0)

    root.password = create_new_hash(prompt("New root password"))

    session.commit()


if __name__ == "__main__":
    manager.run()
