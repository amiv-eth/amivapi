# -*- coding: utf-8 -*-
#
# AMIVAPI util.py
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

import json
import random
import unittest
from base64 import b64encode
from datetime import datetime
import os

import eve_sqlalchemy
from flask.ext.sqlalchemy import SQLAlchemy
from flask.testing import FlaskClient
from flask.wrappers import Response

from amivapi import bootstrap, models, tests
from amivapi.utils import create_new_hash
from amivapi.confirm import token_generator


def find_by_pair(dicts, key, value):
    """ Finds an entry in a list of dicts, which has a pair key => value
    If there is not exactly one result returns None

    This is useful to find an entry in the result of a get query

    Example:

    users = api.get("/users")
    root_user = find_by_pair(users, "username", "root")

    This will find the entry in the response which corresponds to the root
    user
    """
    found = [x for x in dicts if key in x and x[key] == value]
    if len(found) != 1:
        return None
    return found[0]


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
                    kwargs['token'] + ':')
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
        return json.loads(self.data)


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
                if '_etag' not in kwargs:
                    kwargs['_etag'] = 'initial_etag'
                if '_author' not in kwargs:
                    kwargs['_author'] = -1
                if '_created' not in kwargs:
                    kwargs['_created'] = datetime.utcnow()
                if '_updated' not in kwargs:
                    kwargs['_updated'] = datetime.utcnow()

                kwargs = func(self, **kwargs)

                obj = model(**kwargs)

                self.db.add(obj)
                self.db.flush()
                return obj

            return decorated
        return decorate

    @create_object(models.User)
    def new_user(self, **kwargs):
        count = self.next_count()
        if 'username' not in kwargs:
            kwargs['username'] = u"test-user-%i" % count
        if 'firstname' not in kwargs:
            kwargs['firstname'] = u"Test"
        if 'lastname' not in kwargs:
            kwargs['lastname'] = u"User"
        if 'email' not in kwargs:
            kwargs['email'] = u"testuser-%i@example.com" % count
        if 'gender' not in kwargs:
            kwargs['gender'] = random.choice(["male", "female"])
        if 'password' in kwargs:
            kwargs['password'] = create_new_hash(kwargs['password'])
        return kwargs

    @create_object(models.Permission)
    def new_permission(self, **kwargs):
        """ Add a role to a user. You must provide at least user_id and role
        """
        if 'expiry_date' not in kwargs:
            kwargs['expiry_date'] = datetime(3000, 1, 1)
        return kwargs

    @create_object(models.Forward)
    def new_forward(self, **kwargs):
        """ Create a forward """
        count = self.next_count()
        if 'address' not in kwargs:
            kwargs['address'] = u"test-address-%i@example.com" % count
        if 'owner_id' not in kwargs:
            kwargs['owner_id'] = 0
        if 'is_public' not in kwargs:
            kwargs['is_public'] = random.choice([True, False])
        return kwargs

    @create_object(models.ForwardUser)
    def new_forward_user(self, **kwargs):
        """ Add a user to a forward. At least supply the forward_id """
        if 'user_id' not in kwargs:
            kwargs['user_id'] = 0
        return kwargs

    @create_object(models.ForwardAddress)
    def new_forward_address(self, **kwargs):
        """ Add an address to a forward. At least supply the forward_id """
        count = self.next_count()
        if 'email' not in kwargs:
            kwargs['email'] = u"subscriber-%i@example.com" % count
        kwargs['_token'] = token_generator(size=20)
        return kwargs

    @create_object(models.Session)
    def new_session(self, **kwargs):
        """ Create a new session, default is root session """
        if 'user_id' not in kwargs:
            kwargs['user_id'] = 0
        with self.app.app_context():
            kwargs['token'] = b64encode(os.urandom(256))
        return kwargs

    @create_object(models.Event)
    def new_event(self, **kwargs):
        """ Create a new event """
        if 'is_public' not in kwargs:
            kwargs['is_public'] = random.choice([True, False])
        if 'spots' not in kwargs:
            kwargs['spots'] = random.randint(0, 100)
        if 'time_register_start' not in kwargs and kwargs['spots'] >= 0:
            kwargs['time_register_start'] = datetime.now()
        if 'time_register_end' not in kwargs and kwargs['spots'] >= 0:
            kwargs['time_register_end'] = datetime.max
        if 'time_start' not in kwargs:
            kwargs['time_start'] = datetime.now()
        return kwargs

    @create_object(models.EventSignup)
    def new_signup(self, **kwargs):
        """ Create a signup, needs at least the event_id """
        count = self.next_count()
        if 'user_id' not in kwargs:
            kwargs['user_id'] = -1
            kwargs['_email_unreg'] = u"signupper-%i@example.com" % count
            kwargs['_token'] = token_generator(size=20)
        return kwargs

    @create_object(models.JobOffer)
    def new_joboffer(self, **kwargs):
        """ Create a new job offer """
        count = self.next_count()
        if 'company' not in kwargs:
            kwargs['company'] = u"Default company-%i" % count
        return kwargs

    @create_object(models.StudyDocument)
    def new_studydocument(self, **kwargs):
        """ Create a new study document """
        count = self.next_count()
        if 'name' not in kwargs:
            kwargs['name'] = u"Your default studydoc-%i" % count
        return kwargs

    @create_object(models.File)
    def new_file(self, **kwargs):
        """ Create a new file, needs study_doc_id """
        count = self.next_count()
        if 'data' not in kwargs:
            filename = 'default_file_%i.txt' % count
            f = open(os.path.join(self.app.config['STORAGE_DIR'], filename),
                     'w')
            f.write('Your default content.')
            f.close()
            kwargs['data'] = filename
        return kwargs


class WebTestNoAuth(WebTest):
    def setUp(self):
        self.disable_auth = True
        super(WebTestNoAuth, self).setUp()
