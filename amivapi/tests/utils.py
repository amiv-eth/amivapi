# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""General testing utilities."""

import sys
import json
import unittest
import os
from shutil import rmtree
from tempfile import mkdtemp
from itertools import count
from pymongo import MongoClient
from bson import ObjectId
from passlib.context import CryptContext

from flask import g
from flask.testing import FlaskClient
from flask.wrappers import Response

from amivapi.settings import ROOT_PASSWORD
from amivapi.tests.fixtures import FixtureMixin
from amivapi import bootstrap, utils


def find_by_pair(dicts, key, value):
    """Find an entry in a list of dicts, which has a pair key => value.

    If there is not exactly one result returns None

    This is useful to find an entry in the result of a get query

    Example:

    users = api.get("/users")
    root_user = find_by_pair(users, "nethz", "adietmue")

    This will find the entry in the response which corresponds to the root
    user
    """
    found = [x for x in dicts if key in x and x[key] == value]
    if len(found) != 1:
        return None
    return found[0]


def is_file_content(path, content):
    """Check file content.

    Returns true if the file at path exists and has the content in the
    second parameter
    """
    try:
        with open(path, "r") as f:
            if content != f.read():
                return False
    except IOError:
        return False

    return True


class TestClient(FlaskClient):
    """Custom test client with additional request/response checks.

    Auth header will be added if token is provided.
    Data is sent as json if nothing else is specified.
    Responses can be checked against an expected status code.
    """

    def open(self, *args, **kwargs):
        """Modified request.

        Adds token and headers and asserts status code.
        """
        # We are definetly going to add some headers
        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        # Add token
        token = kwargs.pop('token', None)

        if token:
            kwargs['headers'].update({
                # We support a auth header of the form "Token <thetoken>"
                'Authorization': 'Token ' + token
            })

        # Add content-type: json header if nothing else is provided
        if (not("content-type" in kwargs['headers']) and
                ("data" in kwargs)):
            # Parse data
            kwargs['data'] = json.dumps(kwargs['data'])
            # Set header
            kwargs['content_type'] = "application/json"

        # get the actual response and assert status
        expected_code = kwargs.pop('status_code', None)

        response = super(TestClient, self).open(*args, **kwargs)

        status_code = response.status_code

        if (expected_code is not None and expected_code != status_code):
            raise AssertionError(
                "Expected a status code of %i, but got %i instead\n"
                "Response:\n%s\n%s\n%s" % (expected_code, status_code,
                                           response, response.data,
                                           response.status))

        return response


class TestResponse(Response):
    """Custom response to ease JSON handling."""

    @property
    def json(self):
        """Return data in JSON."""
        return json.loads(self.data.decode())


class WebTest(unittest.TestCase, FixtureMixin):
    """Base test class for tests against the full WSGI stack.

    Inspired by eve standard testing class.
    """

    # Test Config overwrites
    test_config = {
        'MONGO_DBNAME': 'test_amivapi',
        'STORAGE_DIR': '',
        'FORWARD_DIR': '',
        'API_MAIL': 'api@test.ch',
        'SMTP_SERVER': '',
        'APIKEYS': {},
        'TESTING': True,
        'DEBUG': True,   # This makes eve's error messages more helpful
        'ENABLE_LDAP': False,  # LDAP test require special treatment
        'PASSWORD_CONTEXT': CryptContext(
            schemes=["pbkdf2_sha256"],

            # default_rounds is used when hashing new passwords, to be varied
            # each time by vary_rounds
            pbkdf2_sha256__default_rounds=10,
            pbkdf2_sha256__vary_rounds=0.1,

            # min_rounds is used to determine if a hash needs to be upgraded
            pbkdf2_sha256__min_rounds=8,
        )
    }

    def setUp(self):
        """Set up the testing client and database connection.

        self.api will be a flask TestClient to make requests
        self.db will be a MongoDB database
        """
        super(WebTest, self).setUp()

        # In 3.2, assertItemsEqual was replaced by assertCountEqual
        # Make assertItemsEqual work in tests for py3 as well
        if sys.version_info >= (3, 2):
            self.assertItemsEqual = self.assertCountEqual

        # create temporary directory for storage
        base_dir = mkdtemp(prefix='amivapi_test')
        self.test_config['STORAGE_DIR'] = os.path.join(base_dir, 'storage')
        self.test_config['FORWARD_DIR'] = os.path.join(base_dir, 'forwards')

        # create eve app and test client
        self.app = bootstrap.create_app(**self.test_config)
        self.app.response_class = TestResponse
        self.app.test_client_class = TestClient
        self.app.test_mails = []

        # Create a separate mongo connection and db reference for tests
        self.connection = MongoClient(self.app.config['MONGO_HOST'],
                                      self.app.config['MONGO_PORT'])
        self.db = self.connection[self.app.config['MONGO_DBNAME']]

        # Assert that database is empty before starting tests.
        assert not self.db.collection_names(), "The database already exists!"

    def tearDown(self):
        """Tear down after testing."""
        # delete testing database
        self.connection.drop_database(self.test_config['MONGO_DBNAME'])
        # close database connection
        self.connection.close()

        # remove temporary folders
        for directory_name in 'STORAGE_DIR', 'FORWARD_DIR':
            directory = self.app.config[directory_name]
            rmtree(directory, ignore_errors=True)

    # Shortcuts to get a token
    counter = count()

    def get_user_token(self, user_id):
        """Create session for a user and return a token.

        Args:
            user_id (str): user_id as string.

        Returns:
            str: Token that can be used to authenticate user.
        """
        token = "test_token_" + str(next(self.counter))
        self.db['sessions'].insert({u'user': ObjectId(user_id),
                                    u'token': token})
        return token

    def get_root_token(self):
        """The root password is the root token.

        Returns:
            str: Token for the root user
        """
        return ROOT_PASSWORD


class WebTestNoAuth(WebTest):
    """WebTest without authentification."""

    def setUp(self):
        """Use auth hook to always authenticate as root for every request."""
        super(WebTestNoAuth, self).setUp()

        def authenticate_root(resource):
            g.current_user = str(self.app.config['ROOT_ID'])
            g.resource_admin = True

        self.app.after_auth += authenticate_root
