# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""General testing utilities."""

import sys
import json
import random
import unittest
from base64 import b64encode
from datetime import datetime, timedelta
import os
from tempfile import mkdtemp
from itertools import count
from pymongo import MongoClient

from flask import g
from flask.testing import FlaskClient
from flask.wrappers import Response
from eve.methods.post import post_internal

from amivapi import bootstrap, utils
from amivapi.utils import token_generator
from mongo_manage import initdb

# Test Config overwrites
test_config = {
    'MONGO_DBNAME': 'test_amivapi',
    'STORAGE_DIR': '',
    'FORWARD_DIR': '',
    'ROOT_MAIL': 'nobody@example.com',
    'SMTP_SERVER': '',
    'APIKEYS': {},
    'TESTING': True,
    'DEBUG': True   # This makes eve's error messages more helpful
}


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


class WebTest(unittest.TestCase):
    """Base test class for tests against the full WSGI stack.

    Inspired by eve standard testing class.
    """

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

        config = utils.get_config()

        # create temporary directories
        test_config['STORAGE_DIR'] = mkdtemp(prefix='amivapi_storage')
        test_config['FORWARD_DIR'] = mkdtemp(prefix='amivapi_forwards')

        # connect to Mongo
        self.connection = MongoClient(config['MONGO_HOST'],
                                      config['MONGO_PORT'])

        # create eve app
        self.app = bootstrap.create_app(**test_config)
        self.app.response_class = TestResponse
        self.app.test_client_class = TestClient

        # connect to testing database and create user
        self.db = self.connection[test_config['MONGO_DBNAME']]

        # Assert that database is empty before starting tests.
        assert not self.db.collection_names(), "The database already exists!"

        # init database
        initdb(self.app)

        # create test client
        self.api = self.app.test_client()

    def tearDown(self):
        """Tear down after testing."""
        # delete testing database
        self.connection.drop_database(test_config['MONGO_DBNAME'])
        # close database connection
        self.connection.close()

        # delete all uploaded files
        self.file_cleanup()

        # remove temporary folders
        os.rmdir(test_config['STORAGE_DIR'])
        os.rmdir(test_config['FORWARD_DIR'])

    def file_cleanup(self):
        """Remove all remaining files."""
        for f in os.listdir(self.app.config['STORAGE_DIR']):
            try:
                os.remove(os.path.join(self.app.config['STORAGE_DIR'], f))
            except:
                # The tests seem to be to fast sometimes, cleanup in the end
                # works fine, in between tests deletion sometimes doesn't work.
                # Hack-like solution: Just ignore that and be happy that all
                # files are deleted in the end.
                # TODO: Find out whats wrong
                # (To reproduce remove the try-except block and run the
                # file access test)
                pass
        for f in os.listdir(self.app.config['FORWARD_DIR']):
            try:
                os.unlink(os.path.join(self.app.config['FORWARD_DIR'], f))
            except Exception as e:
                print(e)

    counter = count()

    def create_object(resource):
        """Decorator for easy object adding."""
        def decorate(func):
            def decorated(self, **kwargs):
                kwargs.setdefault('_etag', "initial_etag")
                # kwargs.setdefault('_author', -1)

                kwargs = func(self, **kwargs)

                with self.app.test_request_context():
                    obj = post_internal(resource,
                                        kwargs,
                                        skip_validation=True)[0]

                # self.db.add(obj)
                # self.db.flush()
                return obj

            return decorated
        return decorate

    @create_object('users')
    def new_user(self, **kwargs):
        """Create user."""
        firstname, gender = random.choice([
            (u"John", "male"), (u"Jane", "female")
        ])

        data = {
            'firstname': firstname,
            'lastname': u"Doe",
            'email': u"testuser-%i@example.com" % next(self.counter),
            'gender': gender,
            'membership': u"none"
        }
        data.update(**kwargs)
        return data

    @create_object('groups')
    def new_group(self, **kwargs):
        """Create group."""
        data = {
            'name': u"test-group-%i" % next(self.counter),
            'moderator_id': 0,
            'allow_self_enrollment': random.choice([True, False]),
            'has_zoidberg_share': random.choice([True, False]),
        }
        data.update(kwargs)
        return data

    @create_object('groupaddresses')
    def new_group_address(self, **kwargs):
        """Create group address. At least supply the group_id."""
        kwargs.setdefault('email',
                          u"adress-%i@example.com" % next(self.counter))
        return kwargs

    @create_object('groupmembers')
    def new_group_member(self, **kwargs):
        """Add a user to a group. At least supply the group_id."""
        kwargs.setdefault('user_id', 0)
        return kwargs

    @create_object('groupforwards')
    def new_group_forward(self, **kwargs):
        """Add a user to a group. At least supply the group_id."""
        kwargs.setdefault('email',
                          u"forward-%i@example.com" % next(self.counter))
        return kwargs

    @create_object('sessions')
    def new_session(self, **kwargs):
        """Create a new session, default is root session."""
        kwargs.setdefault('user_id', 0)

        with self.app.app_context():
            kwargs['token'] = b64encode(os.urandom(256)).decode('utf_8')

        return kwargs

    @create_object('events')
    def new_event(self, **kwargs):
        """Create a new event."""
        data = {
            'allow_email_signup': random.choice([True, False]),
            'spots': random.randint(0, 100),
            'time_register_start': datetime.utcnow() - timedelta(days=14),
            'time_register_end': datetime.utcnow() + timedelta(days=14),
            'time_start': datetime.utcnow() + timedelta(days=7),
        }
        data.update(kwargs)
        return data

    @create_object('eventsignups')
    def new_signup(self, **kwargs):
        """Create a signup, needs at least the event_id."""
        if 'user_id' not in kwargs:
            count = next(self.counter)
            kwargs['user_id'] = -1
            kwargs['_email_unreg'] = u"signupper-%i@example.com" % count
            kwargs['_token'] = token_generator(size=20)
        return kwargs

    @create_object('joboffers')
    def new_joboffer(self, **kwargs):
        """Create a new job offer."""
        kwargs.setdefault('company', u"ACME Inc. %i" % next(self.counter))
        return kwargs

    @create_object('studydocuments')
    def new_studydocument(self, **kwargs):
        """Create a new study document."""
        kwargs.setdefault('name', u"Example Exam %i" % next(self.counter))
        return kwargs

    @create_object('files')
    def new_file(self, **kwargs):
        """Create a new file, needs study_doc_id."""
        if 'data' not in kwargs:
            filename = 'default_file_%i.txt' % next(self.counter)
            with open(os.path.join(self.app.config['STORAGE_DIR'], filename),
                      'wb') as f:
                f.write("Some example content.")

            kwargs['data'] = filename
        return kwargs

    # Shortcuts to get a token

    def get_user_token(self, user_id):
        """Create session for a user and return a token.

        Args:
            user_id (str): user_id as string.

        Returns:
            str: Token that can be used to authenticate user.
        """
        token = "test_token_" + str(next(self.counter))
        self.db['sessions'].insert({u'user_id': user_id,
                                    u'token': token})
        return token

    def get_root_token(self):
        """Create session for root user and return token.

        Returns:
            str: Token for the root user
        """
        return self.get_user_token(24 * "0")


class WebTestNoAuth(WebTest):
    """WebTest without authentification."""

    def setUp(self):
        """Use auth hook to always authenticate as root for every request."""
        super(WebTestNoAuth, self).setUp()

        def authenticate_root(resource):
            g.current_user = str(self.app.config['ROOT_ID'])
            g.resource_admin = True

        self.app.after_auth += authenticate_root
