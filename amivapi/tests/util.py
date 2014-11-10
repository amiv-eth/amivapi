import json
import unittest

from eve.io.sql import sql
from flask.ext.sqlalchemy import SQLAlchemy
from flask.testing import FlaskClient
from flask.wrappers import Response

from amivapi import bootstrap, tests


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
                "Expected a status code of %i, but got %i instead"
                % (expected_code, status_code))

        return response


class TestResponse(Response):
    """Custom response to ease JSON handling."""
    @property
    def json(self):
        return json.loads(self.data)


class WebTest(unittest.TestCase):
    """Base test class for tests against the full WSGI stack."""

    def setUp(self):
        super(WebTest, self).setUp()

        transaction = tests.connection.begin()
        self.addCleanup(transaction.rollback)

        # Monkey-patch the session used by Eve to join the global transaction
        sql.db = SQLAlchemy(session_options={'bind': tests.connection})
        sql.SQL.driver = sql.db

        app = bootstrap.create_app("testing")
        app.response_class = TestResponse
        app.test_client_class = TestClient

        self.db = app.data.driver.session
        self.addCleanup(self.db.remove)

        # Prevent Eve/Flask-SQLAlchemy from removing or commiting the session,
        # which would break our base transaction
        self.db.commit = self.db.flush
        self.db.remove = self.db.flush

        self.api = app.test_client()
