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
from amivapi.confirm import id_generator


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
        if 'address' not in kwargs:
            kwargs['address'] = u"subscriber-%i@example.com" % count
        return kwargs

    @create_object(models.Session)
    def new_session(self, **kwargs):
        """ Create a new session, default is root session """
        if 'user_id' not in kwargs:
            kwargs['user_id'] = 0
        with self.app.app_context():
            kwargs['token'] = create_token(kwargs['user_id'])
        return kwargs

    @create_object(models.Event)
    def new_event(self, **kwargs):
        """ Create a new event """
        if 'is_public' not in kwargs:
            kwargs['is_public'] = random.choice([True, False])
        if 'spots' not in kwargs:
            kwargs['spots'] = random.randint(0, 100)
        return kwargs

    @create_object(models.EventSignup)
    def new_signup(self, **kwargs):
        """ Create a signup, needs at least the event_id """
        count = self.next_count()
        if 'user_id' not in kwargs:
            kwargs['user_id'] = -1
            kwargs['email'] = u"signupper-%i@example.com" % count
        return kwargs

    @create_object(models.JobOffer)
    def new_joboffer(self, **kwargs):
        """ Create a new job offer """
        count = self.next_count()
        if 'title' not in kwargs:
            kwargs['title'] = u"Your job at default company-%i" % count
        return kwargs

    @create_object(models.Confirm)
    def new_confirm(self, **kwargs):
        """ Creates a new confirm action. You must provide resource, data
        and method """
        if 'token' not in kwargs:
            kwargs['token'] = "%i" % id_generator()
        if 'expiry_date' not in kwargs:
            kwargs['expiry_date'] = datetime(3000, 1, 1)
        return kwargs


class WebTestNoAuth(WebTest):
    def setUp(self):
        self.disable_auth = True
        super(WebTestNoAuth, self).setUp()
