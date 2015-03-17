# -*- coding: utf-8 -*-
#
# AMIVAPI __init__.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import warnings
import string
import random
from tempfile import NamedTemporaryFile, mkdtemp
from os import unlink, rmdir

from sqlalchemy import create_engine

from amivapi import bootstrap, utils


engine = None
connection = None
dbname = None

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
    global engine, connection, dbname
    warnings.filterwarnings('error', module=r'^sqlalchemy')

    config = utils.get_config()

    # Create a random database
    if config['TESTS_IN_DB'] and config['DB_TYPE'] == 'mysql':
        dbname = ('test_' +
                  ''.join(random.choice(string.ascii_lowercase + string.digits)
                          for _ in range(10)))
        tmpengine = create_engine("mysql+mysqlconnector://%s:%s@%s" %
                                  (config['DB_USER'], config['DB_PASS'],
                                   config['DB_HOST']))
        tmpengine.connect().execute("CREATE DATABASE %s" % dbname)

        db_uri = ("mysql+mysqlconnector://%s:%s@%s/%s?charset=utf8" %
                  (config['DB_USER'], config['DB_PASS'],
                   config['DB_HOST'], dbname))
    else:
        # Use tempfile for database
        db_file = NamedTemporaryFile(delete=False,
                                     prefix='testdb_',
                                     suffix='.db')
        dbname = db_file.name
        db_file.close()
        db_uri = "sqlite:///%s" % dbname

    test_config['SQLALCHEMY_DATABASE_URI'] = db_uri
    test_config['STORAGE_DIR'] = mkdtemp(prefix='amivapi_storage')
    test_config['FORWARD_DIR'] = mkdtemp(prefix='amivapi_forwards')

    # Connect to the created database
    engine = create_engine(db_uri)
    connection = engine.connect()

    bootstrap.init_database(connection, config)


def teardown():
    """Drop database created above"""
    connection.close()

    config = bootstrap.get_config()

    # Delete the test database

    if config['TESTS_IN_DB'] and config['DB_TYPE'] == 'mysql':
        tmpengine = create_engine("mysql+mysqlconnector://%s:%s@%s" %
                                  (config['DB_USER'], config['DB_PASS'],
                                   config['DB_HOST']))
        tmpengine.connect().execute("DROP DATABASE %s" % dbname)
    else:
        unlink(dbname)

    # Remove test folders
    rmdir(test_config['STORAGE_DIR'])
    rmdir(test_config['FORWARD_DIR'])
