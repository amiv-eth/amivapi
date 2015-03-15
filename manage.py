import codecs
import datetime as dt
from os import mkdir, urandom
from os.path import abspath, dirname, join, exists, expanduser
from pprint import pprint
from base64 import b64encode

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError

from flask import Flask
from flask.ext.script import (
    Manager,
    prompt,
    prompt_bool,
    prompt_choices,
    prompt_pass,
)

from amivapi import settings, models, schemas
from amivapi.models import User
from amivapi.utils import create_new_hash, get_config
from amivapi.bootstrap import init_database


manager = Manager(Flask("amivapi"))
# This must be the same as in amivapi.utils.get_config
config_path = join(settings.ROOT_DIR, "config.cfg")


#
# Utility functions
#


def save_config(name, **config):
    config_dir = dirname(name)
    if not exists(config_dir):
        mkdir(config_dir, 0700)

    with codecs.open(name, "w", encoding="utf-8") as f:
        f.write('# Automatically generated on %s\n\n'
                % dt.datetime.utcnow())

        for key, value in sorted(config.items()):
            if key not in dir(settings) or value != getattr(settings, key):
                f.write("%s = %r\n" % (key.upper(), value))
#
# API Key management
#


@manager.command
def change_apikey(permissions):
    resources = schemas.get_domain().keys()

    while True:
        print("Change apikey:")
        pprint(permissions)

        i = 1
        for res in resources:
            print(str(i) + ": " + res)
            i += 1
        print("s: save")
        options = map(lambda i: str(i + 1), range(len(resources))) + ['s']
        choice = prompt_choices("Choose resource to change",
                                options,
                                "s")
        if choice == "s":
            return
        resource = resources[int(choice) - 1]

        method = prompt_choices("Choose method to toggle",
                                ['get', 'post', 'patch', 'put', 'delete'])

        if (resource not in permissions
                or method not in permissions[resource]
                or not permissions[resource][method]):
            if resource not in permissions:
                permissions[resource] = {}
            permissions[resource][method] = 1
        else:
            del permissions[resource][method]
            if len(permissions[resource]) == 0:
                del permissions[resource]

        print("\n")


@manager.command
def apikeys_add():
    """ Adds a new API key """

    cfg = get_config()

    name = prompt("What purpose does the key have?")
    newkey = b64encode(urandom(512))

    if "APIKEYS" not in cfg:
        cfg['APIKEYS'] = {}
    permissions = cfg['APIKEYS'][newkey] = {"name": name}
    change_apikey(permissions)

    save_config(config_path, **cfg)
    print("\nSaved key %s:\n" % name)
    print(newkey)


@manager.command
def apikeys_list():

    cfg = get_config()

    for token, entry in cfg['APIKEYS'].iteritems():
        name = entry['name']
        print("=== %s ===\n\n%s\n" % (name, token))


@manager.command
def choose_apikey(cfg):
    keys = cfg['APIKEYS'].keys()
    names = map(lambda entry: entry['name'], cfg['APIKEYS'].values())

    i = 1
    for n in names:
        print("%i: %s" % (i, n))
        i += 1

    options = map(lambda i: str(i + 1), range(len(names)))
    choice = prompt_choices("Choose API key to change", options)

    return keys[int(choice) - 1]


@manager.command
def apikeys_edit():
    cfg = get_config()

    key = choose_apikey(cfg)

    permissions = cfg['APIKEYS'][key]
    change_apikey(permissions)

    save_config(config_path, **cfg)
    print("Saved key: %s" % permissions['name'])


@manager.command
def apikeys_delete():
    cfg = get_config()

    key = choose_apikey(cfg)
    sure = prompt_choices("Are you sure?", ["y", "n"], "n")

    if sure == "y":
        del cfg['APIKEYS'][key]
        save_config(config_path, **cfg)


#
# Create new config
#


@manager.option("-f", "--force", dest="force",
                help="Force to overwrite existing config")
@manager.option("--debug", dest="debug")
@manager.option("--db-type", dest="db_type")
@manager.option("--db-user", dest="db_user")
@manager.option("--db-pass", dest="db_pass")
@manager.option("--db-host", dest="db_host")
@manager.option("--db-name", dest="db_name")
@manager.option("--tests-in-db", dest="tests_in_db")
@manager.option("--file-dir", dest="file_dir")
@manager.option("--root-mail", dest="root_mail")
@manager.option("--smtp", dest="smtp_server")
@manager.option("--forward-dir", dest="forward_dir")
def create_config(force=False,
                  debug=None,
                  db_type=None,
                  db_user=None,
                  db_pass=None,
                  db_host=None,
                  db_name=None,
                  tests_in_db=None,
                  file_dir=None,
                  root_mail=None,
                  smtp_server=None,
                  forward_dir=None):
    """Creates a new configuration.

    The config is stored in ROOT/config.cfg
    """

    if exists(config_path) and not force:
        if not prompt_bool("The file config.cfg already exists, "
                           "do you want to overwrite it?"):
            return

    if not debug:
        debug = prompt_bool("Activate debug mode?")

    # Configuration values
    config = {
        'DEBUG': debug,
    }

    # Ask for database settings
    db_uri = None
    if not db_type:
        db_type = prompt_choices("Choose the type of database",
                                 ["sqlite", "mysql"],
                                 default="sqlite")
    elif db_type not in ['sqlite', 'mysql']:
        print("Only sqlite and mysql supported as db type!")
        exit(0)

    config['DB_TYPE'] = db_type

    if db_type == "sqlite":
        db_filepath = prompt("Path to db file (including filename)",
                             default=join(settings.ROOT_DIR, "data.db"))
        config['DB_FILEPATH'] = db_filepath
        db_uri = "sqlite:///%s" % abspath(expanduser(db_filepath))
        tests_in_db = False

    elif db_type == "mysql":
        if not db_user:
            db_user = prompt("MySQL username", default="amivapi")
            db_pass = prompt_pass("MySQL password", default="")
        elif not db_pass:
            db_pass = ""
        if not db_host:
            db_host = prompt("MySQL host", default="localhost")
        if not db_name:
            db_name = prompt("MySQL database", default="amivapi")

        if not tests_in_db:
            tests_in_db = prompt_bool(
                "Should the DB server also be used for tests?")

        config['DB_HOST'] = db_host
        config['DB_USER'] = db_user
        config['DB_PASS'] = db_pass
        config['DB_NAME'] = db_name

        db_uri = "mysql+mysqlconnector://%s:%s@%s/%s?charset=utf8" % \
            (db_user, db_pass, db_host, db_name)

    config['TESTS_IN_DB'] = tests_in_db
    config['SQLALCHEMY_DATABASE_URI'] = db_uri

    if not file_dir:
        file_dir = abspath(expanduser(prompt("Path to file storage folder",
                                             default=join(settings.ROOT_DIR,
                                                          "filestorage"))))

    config['STORAGE_DIR'] = file_dir

    if not root_mail:
        root_mail = prompt("Maintainer E-Mail")
    config['ROOT_MAIL'] = root_mail

    if not smtp_server:
        smtp_server = prompt("SMTP Server to send mails",
                             default='localhost')
    config['SMTP_SERVER'] = smtp_server

    if not forward_dir:
        forward_dir = prompt("Directory where forwards are stored",
                             default=join(settings.ROOT_DIR, "forwards"))
    config['FORWARD_DIR'] = abspath(expanduser(forward_dir))

    if not exists(file_dir):
        mkdir(file_dir, 0700)

    if not exists(config['FORWARD_DIR']):
        mkdir(config['FORWARD_DIR'], 0700)

    config['APIKEYS'] = {}

    # Write everything to file
    # Note: The file is opened in non-binary mode, because we want python to
    # auto-convert newline characters to the underlying platform.
    save_config(config_path, **config)

    engine = create_engine(config['SQLALCHEMY_DATABASE_URI'])
    try:
        print("Setting up database...")
        init_database(engine, config)
    except (OperationalError, ProgrammingError):
        if not force and not prompt_bool(
                "A database seems to exist already. Overwrite it?(y/N)"):
            return
        models.Base.metadata.drop_all(engine)
        init_database(engine, config)


#
# Change root password
#


@manager.command
def set_root_password():
    """Sets the root password. """

    cfg = get_config()

    engine = create_engine(cfg['SQLALCHEMY_DATABASE_URI'])
    sessionmak = sessionmaker(bind=engine)
    session = sessionmak()

    try:
        root = session.query(User).filter(User.id == 0).one()
    except (OperationalError, ProgrammingError):
        print ("No root user found, please recreate the config to set up a"
               " database.")
        exit(0)

    root.password = create_new_hash(prompt("New root password"))

    session.commit()
    session.close()


#
#
# Run the FlaskScript manager
#
#


if __name__ == "__main__":
    manager.run()
