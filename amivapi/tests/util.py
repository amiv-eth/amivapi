import json
import random
import unittest
from base64 import b64encode
from datetime import datetime

from eve.io.sql import sql
from flask.ext.sqlalchemy import SQLAlchemy
from flask.testing import FlaskClient
from flask.wrappers import Response

from amivapi import bootstrap, models, tests
from amivapi.auth import create_new_hash, create_token


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

        if "data" in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
            kwargs['content_type'] = "application/json"

        response = super(TestClient, self).open(*args, **kwargs)
        status_code = response.status_code
        if (expected_code is not None and expected_code != status_code):
            raise AssertionError(
                "Expected a status code of %i, but got %i instead\n"
                % (expected_code, status_code) + "Response:\n%s\n%s"
                % (response, response.json))

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
        sql.db = SQLAlchemy(session_options={'bind': tests.connection})
        sql.SQL.driver = sql.db

        self.app = bootstrap.create_app("testing",
                                        disable_auth=self.disable_auth)
        self.app.response_class = TestResponse
        self.app.test_client_class = TestClient

        self.db = self.app.data.driver.session
        self.addCleanup(self.db.remove)

        # Prevent Eve/Flask-SQLAlchemy from removing or commiting the session,
        # which would break our base transaction
        self.db.commit = self.db.flush
        self.db.remove = self.db.flush

        self.api = self.app.test_client()

    _count = 0

    def next_count(self):
        self._count += 1
        return self._count

    def add_metafields(func):
        def decorated(self, *args, **kwargs):
            if '_etag' not in kwargs:
                kwargs['_etag'] = 'initial_etag'
            if '_author' not in kwargs:
                kwargs['_author'] = -1
            if '_created' not in kwargs:
                kwargs['_created'] = datetime.utcnow()
            if '_updated' not in kwargs:
                kwargs['_updated'] = datetime.utcnow()

            return func(self, *args, **kwargs)
        return decorated

    @add_metafields
    def new_user(self, **kwargs):
        count = self.next_count()
        if 'password' in kwargs:
            kwargs['password'] = create_new_hash(kwargs['password'])

        user = models.User(username=u"test-user-%i" % count,
                           firstname=u"Test",
                           lastname=u"Use" + ("r" * count),
                           email=u"testuser-%i@example.net" % count,
                           gender=random.choice(["male", "female"]),
                           **kwargs)
        self.db.add(user)
        self.db.flush()
        return user

    @add_metafields
    def new_session(self, **kwargs):
        if 'user_id' not in kwargs:
            kwargs['user_id'] = 0
        if 'token' not in kwargs:
            with self.app.app_context():
                kwargs['token'] = create_token(kwargs['user_id'])

        session = models.Session(**kwargs)
        self.db.add(session)
        self.db.flush()
        return session


class WebTestNoAuth(WebTest):
    def setUp(self):
        self.disable_auth = True
        super(WebTestNoAuth, self).setUp()
