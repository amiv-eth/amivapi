# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import json
import random
import unittest
from base64 import b64encode
from datetime import datetime, timedelta
import os

import eve_sqlalchemy
from flask.ext.sqlalchemy import SQLAlchemy
from flask.testing import FlaskClient
from flask.wrappers import Response

from amivapi import bootstrap, models, tests
from amivapi.utils import token_generator
from amivapi.auth import Session
from amivapi.events import Event, EventSignup
from amivapi.groups import Group, GroupAddress, GroupMember, GroupForward
from amivapi.joboffers import JobOffer
from amivapi.studydocs import StudyDocument, File


def find_by_pair(dicts, key, value):
    """ Finds an entry in a list of dicts, which has a pair key => value
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
    """
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

    Requests are enforced to be JSON (data and content type).
    Responses can be checked against an expected status code.
    """
    def open(self, *args, **kwargs):
        expected_code = kwargs.pop('status_code', None)

        if 'token' in kwargs:
            if 'headers' not in kwargs:
                kwargs['headers'] = {}

            kwargs['headers'].update({
                'Authorization': 'Basic ' + b64encode(
                    kwargs['token'].encode('utf_8') + b':').decode('utf_8')
            })

            kwargs.pop('token', None)

        if (not(("headers" in kwargs)
                and ("content-type" in kwargs['headers']))
                and ("data" in kwargs)):
            kwargs['data'] = json.dumps(kwargs['data'])
            kwargs['content_type'] = "application/json"

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
        return json.loads(self.data.decode())


class WebTest(unittest.TestCase):
    """Base test class for tests against the full WSGI stack."""

    disable_auth = False

    def setUp(self):
        super(WebTest, self).setUp()

        transaction = tests.connection.begin()
        self.addCleanup(transaction.rollback)

        # Monkey-patch the session used by Eve to join the global transaction
        eve_sqlalchemy.db = SQLAlchemy(
            session_options={'bind': tests.connection})
        eve_sqlalchemy.SQL.driver = eve_sqlalchemy.db

        self.app = bootstrap.create_app(disable_auth=self.disable_auth,
                                        **tests.test_config)
        self.app.response_class = TestResponse
        self.app.test_client_class = TestClient

        self.db = self.app.data.driver.session
        self.addCleanup(self.db.remove)

        # Prevent Eve/Flask-SQLAlchemy from removing or commiting the session,
        # which would break our base transaction
        self.db.commit = self.db.flush
        self.db.remove = self.db.flush

        self.api = self.app.test_client()

        # Delete all files after testing
        self.addCleanup(self.file_cleanup)

    def file_cleanup(self):
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

    def assert_count(self, model, count):
        model_count = self.db.query(model).count()
        self.assertEquals(count, model_count)

    _count = 0

    def next_count(self):
        self._count += 1
        return self._count

    def create_object(model):
        def decorate(func):
            def decorated(self, **kwargs):
                kwargs.setdefault('_etag', "initial_etag")
                kwargs.setdefault('_author', -1)

                kwargs = func(self, **kwargs)
                obj = model(**kwargs)

                self.db.add(obj)
                self.db.flush()
                return obj

            return decorated
        return decorate

    @create_object(models.User)
    def new_user(self, **kwargs):
        firstname, gender = random.choice([
            (u"John", "male"), (u"Jane", "female")
        ])

        data = {
            'firstname': firstname,
            'lastname': u"Doe",
            'email': u"testuser-%i@example.com" % self.next_count(),
            'gender': gender,
        }
        data.update(**kwargs)
        return data

    @create_object(Group)
    def new_group(self, **kwargs):
        """ Create a forward """
        data = {
            'name': u"test-group-%i" % self.next_count(),
            'moderator_id': 0,
            'allow_self_enrollment': random.choice([True, False]),
            'has_zoidberg_share': random.choice([True, False]),
        }
        data.update(kwargs)
        return data

    @create_object(GroupAddress)
    def new_group_address(self, **kwargs):
        """ Add a forward address. At least supply the group_id """
        kwargs.setdefault('email',
                          u"adress-%i@example.com" % self.next_count())
        return kwargs

    @create_object(GroupMember)
    def new_group_member(self, **kwargs):
        """ Add a user to a group. At least supply the group_id """
        kwargs.setdefault('user_id', 0)
        return kwargs

    @create_object(GroupForward)
    def new_group_forward(self, **kwargs):
        """ Add a user to a group. At least supply the group_id """
        kwargs.setdefault('email',
                          u"forward-%i@example.com" % self.next_count())
        return kwargs

    @create_object(Session)
    def new_session(self, **kwargs):
        """ Create a new session, default is root session """
        kwargs.setdefault('user_id', 0)

        with self.app.app_context():
            kwargs['token'] = b64encode(os.urandom(256)).decode('utf_8')

        return kwargs

    @create_object(Event)
    def new_event(self, **kwargs):
        """ Create a new event """
        data = {
            'allow_email_signup': random.choice([True, False]),
            'spots': random.randint(0, 100),
            'time_register_start': datetime.utcnow() - timedelta(days=14),
            'time_register_end': datetime.utcnow() + timedelta(days=14),
            'time_start': datetime.utcnow() + timedelta(days=7),
        }
        data.update(kwargs)
        return data

    @create_object(EventSignup)
    def new_signup(self, **kwargs):
        """ Create a signup, needs at least the event_id """
        if 'user_id' not in kwargs:
            count = self.next_count()
            kwargs['user_id'] = -1
            kwargs['_email_unreg'] = u"signupper-%i@example.com" % count
            kwargs['_token'] = token_generator(size=20)
        return kwargs

    @create_object(JobOffer)
    def new_joboffer(self, **kwargs):
        """ Create a new job offer """
        kwargs.setdefault('company', u"ACME Inc. %i" % self.next_count())
        return kwargs

    @create_object(StudyDocument)
    def new_studydocument(self, **kwargs):
        """ Create a new study document """
        kwargs.setdefault('name', u"Example Exam %i" % self.next_count())
        return kwargs

    @create_object(File)
    def new_file(self, **kwargs):
        """ Create a new file, needs study_doc_id """
        if 'data' not in kwargs:
            filename = 'default_file_%i.txt' % self.next_count()
            with open(os.path.join(self.app.config['STORAGE_DIR'], filename),
                      'wb') as f:
                f.write("Some example content.")

            kwargs['data'] = filename
        return kwargs


class WebTestNoAuth(WebTest):
    disable_auth = True
