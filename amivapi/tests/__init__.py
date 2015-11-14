# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import warnings
import random
from tempfile import NamedTemporaryFile, mkdtemp
from os import unlink, rmdir

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url

from amivapi import bootstrap, utils


engine = None
connection = None

# Config overwrites
test_config = {
    'SQLALCHEMY_DATABASE_URI': '',
    'STORAGE_DIR': '',
    'FORWARD_DIR': '',
    'ROOT_MAIL': 'nobody@example.com',
    'SMTP_SERVER': '',
    'APIKEYS': {},
    'TESTING': True,
    'DEBUG': False
}


def setup():
    global engine, connection
    warnings.filterwarnings('error', module=r'^sqlalchemy')

    config = utils.get_config()
    db_uri = config['SQLALCHEMY_DATABASE_URI']

    # Create a random database
    if config['TESTS_IN_DB'] and db_uri.startswith("mysql"):
        db_name = "test-%d" % random.randint(0, 10**6)
    else:
        # Use tempfile for database
        db_file = NamedTemporaryFile(delete=False,
                                     prefix='testdb_',
                                     suffix='.db')
        db_name = db_file.name
        db_file.close()

        db_uri = "sqlite:///"

    db_url = make_url(db_uri)
    engine = create_engine(db_url)

    # Connect and create the test database
    connection = engine.connect()
    connection.execute("CREATE DATABASE `%s`" % db_name)
    connection.execute("USE `%s`" % db_name)
    connection.execute("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO'")

    # Update test configuration
    db_url.database = db_name
    test_config['SQLALCHEMY_DATABASE_URI'] = str(db_url)
    test_config['STORAGE_DIR'] = mkdtemp(prefix='amivapi_storage')
    test_config['FORWARD_DIR'] = mkdtemp(prefix='amivapi_forwards')

    # Create tables
    bootstrap.init_database(connection, config)


def teardown():
    """Drop database created above"""
    db_name = engine.url.database

    connection.execute("DROP DATABASE `%s`" % db_name)
    connection.close()

    if engine.url.drivername == "sqlite":
        unlink(db_name)

    # Remove test folders
    rmdir(test_config['STORAGE_DIR'])
    rmdir(test_config['FORWARD_DIR'])
