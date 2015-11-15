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
    use_mysql = config['TESTS_IN_DB'] and db_uri.startswith("mysql")

    if use_mysql:
        db_name = "test-%d" % random.randint(0, 10**6)
    else:
        # Use tempfile for database
        with NamedTemporaryFile(delete=False,
                                prefix='testdb-',
                                suffix='.db') as db_file:
            db_name = db_file.name

        # Use in-memory sqlite database
        db_uri = "sqlite:///%s" % db_name

    db_url = make_url(db_uri)
    engine = create_engine(db_url)

    # Connect and create the test database
    connection = engine.connect()
    if use_mysql:
        connection.execute("CREATE DATABASE `%s`" % db_name)
        connection.execute("USE `%s`" % db_name)
        db_url.database = db_name

    # Update test configuration
    test_config['SQLALCHEMY_DATABASE_URI'] = str(db_url)
    test_config['STORAGE_DIR'] = mkdtemp(prefix='amivapi_storage')
    test_config['FORWARD_DIR'] = mkdtemp(prefix='amivapi_forwards')

    # Create tables
    bootstrap.init_database(connection, config)


def teardown():
    """Drop database created above"""
    db_name = engine.url.database

    if engine.dialect.name == "sqlite":
        unlink(db_name)
    else:
        connection.execute("DROP DATABASE `%s`" % db_name)
        connection.close()

    # Remove test folders
    rmdir(test_config['STORAGE_DIR'])
    rmdir(test_config['FORWARD_DIR'])
