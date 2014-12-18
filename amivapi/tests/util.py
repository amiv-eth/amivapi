import json
import random
import unittest

from eve.io.sql import sql
from flask.ext.sqlalchemy import SQLAlchemy
from flask.testing import FlaskClient
from flask.wrappers import Response

from amivapi import bootstrap, models, tests
from amivapi.auth import create_new_hash


class TestClient(FlaskClient):
    """Custom test client with additional request/response checks.

    Requests are enforced to be JSON (data and content type).
    Responses can be checked against an expected status code.
    """
    def open(self, *args, **kwargs):
        expected_code = kwargs.pop('status_code', None)

        if "data" in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
            kwargs['content_type'] = "application/json"

        response = super(TestClient, self).open(*args, **kwargs)
        status_code = response.status_code
        if (expected_code is not None and expected_code != status_code):
            raise AssertionError(
                "Expected a status code of %i, but got %i instead\n"
                % (expected_code, status_code) + "Response: %s"
                % response.json)

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

        self.app = bootstrap.create_app("testing", disable_auth=self.disable_auth)
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

    def new_user(self, **kwargs):
        count = self.next_count()
        if 'password' in kwargs:
            kwargs['password'] = create_new_hash(kwargs['password'])

        user = models.User(username=u"test-user-%i" % count,
                           firstname=u"Test",
                           lastname=u"Use" + ("r" * count),
                           email=u"testuser-%i@example.net" % count,
                           gender=random.choice(["male", "female"]),
                           _author=0,
                           **kwargs)
        self.db.add(user)
        self.db.flush()
        return user


class WebTestNoAuth(WebTest):
    def setUp(self):
        self.disable_auth = True
        super(WebTestNoAuth, self).setUp()
