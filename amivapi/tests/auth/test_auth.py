# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for auth functions."""

from base64 import b64encode
from datetime import datetime as dt, timedelta, timezone

from bson import ObjectId
from flask import g
from werkzeug.exceptions import Forbidden, Unauthorized

from amivapi.auth import (
    abort_if_not_public,
    add_lookup_filter,
    AmivTokenAuth,
    authenticate,
    check_if_admin,
    check_item_write_permission,
    check_resource_write_permission
)
from amivapi.auth.auth import (
    not_if_admin,
    not_if_admin_or_readonly_admin,
    only_amiv_token_auth,
    only_if_auth_required
)
from amivapi.tests.auth.fake_auth import FakeAuthTest
from amivapi.tests.utils import WebTest


class AmivTokenAuthTest(WebTest):
    """Tests for `AmivTokenAuth` default methods."""

    def test_amiv_token_auth_authorized(self):
        """Test the function `authorized` called by Eve.

        For AmivTokenAuth (and subclasses) it should always return True,
        since everything is handled elsewhere. For this it needs to set
        g.auth_required to True.
        """
        test_auth = AmivTokenAuth()
        with self.app.app_context():
            # No g.auth_required before
            with self.assertRaises(AttributeError):
                g.auth_required
            # Always return true
            self.assertTrue(test_auth.authorized(None, None, None))
            # set g.auth_required
            self.assertTrue(g.auth_required)

    def test_amiv_token_auth_create_user_lookup_filter(self):
        """Test default lookup filter. Should be None."""
        auth = AmivTokenAuth()
        self.assertEquals(auth.create_user_lookup_filter(None), {})

    def test_amiv_token_auth_has_item_write_permission(self):
        """Test default write permission. Should be False."""
        auth = AmivTokenAuth()
        self.assertFalse(auth.has_item_write_permission(None, None))

    def test_amiv_token_auth_has_resource_write_permission(self):
        """Test default write permission. Should be False."""
        auth = AmivTokenAuth()
        self.assertFalse(auth.has_resource_write_permission(None))


class DecoratorTest(FakeAuthTest):
    """Unittests for the decorators that require auth etc."""

    def test_func(self, *args):
        """Create a small function that remembers if its been called."""
        self.was_called = True
        self.call_args = args

    def assertDecorated(self, decorator, context, was_called,
                        func_args=None, call_args=None):
        """Test a decorator.

        Use it to decorate the test function, init context and call the
        decorated function with func_args.
        Then check was_called and call_args (if needed).
        """
        self.was_called = False
        self.call_args = []
        if not func_args:
            func_args = []

        decorated = decorator(self.test_func)
        with self._init_context(**context):
            decorated(*func_args)
            self.assertEqual(was_called, self.was_called)
            if call_args:
                self.assertItemsEqual(call_args, self.call_args)

    def test_auth_required_decorator(self):
        """Call function only if g.get('auth_required')."""
        dec = only_if_auth_required
        self.assertDecorated(dec, {}, False)
        self.assertDecorated(dec, {'auth_required': False}, False)
        self.assertDecorated(dec, {'auth_required': True}, True)

    def test_not_if_admin(self):
        """Call function only if g.resource_admin."""
        dec = not_if_admin
        self.assertDecorated(dec, {'resource_admin': False}, True)
        self.assertDecorated(dec, {'resource_admin': True}, False)

    def test_not_if_admin_readonly(self):
        """Call function only if not admin or readonly admin."""
        dec = not_if_admin_or_readonly_admin
        self.assertDecorated(dec,
                             {'resource_admin': False,
                              'resource_admin_readonly': False},
                             True)
        self.assertDecorated(dec,
                             {'resource_admin': True,
                              'resource_admin_readonly': False},
                             False)
        self.assertDecorated(dec,
                             {'resource_admin': False,
                              'resource_admin_readonly': True},
                             False)
        self.assertDecorated(dec,
                             {'resource_admin': True,
                              'resource_admin_readonly': True},
                             False)

    def test_only_amiv_token_auth(self):
        """Make sure functions is called with auth as arg for AmivTokenAuth."""
        dec = only_amiv_token_auth
        auth = self.app.config['DOMAIN']['fake']['authentication']
        for resource in ['fake_nothing', 'fake_no_amiv']:
            self.assertDecorated(dec, {}, False, func_args=[resource])

        self.assertDecorated(dec, {}, True,
                             func_args=['fake'], call_args=[auth, 'fake'])


class AuthFunctionTest(FakeAuthTest):
    """Unittests for the auth functions."""

    # Tests for add_lookup_filter

    def test_lookup_added(self):
        """Test if lookup filters are added."""
        user = 'does not matter'
        lookup = {}
        expected = {'$and': [{'_id': user}]}

        with self._init_context(current_user=user, auth_required=True):
            add_lookup_filter('fake', None, lookup)
            self.assertEqual(lookup, expected)

    def test_added_lookup_doesnt_overwrite_existing_and(self):
        """Test that lookup filters are added to existing $and."""
        user = 'test'
        lookup = {'$and': ['already_here']}
        expected = {'$and': ['already_here', {'_id': user}]}

        with self._init_context(current_user=user, auth_required=True):
            add_lookup_filter('fake', None, lookup)
            self.assertEqual(lookup, expected)

    # Tests for `check_write_permission`

    def test_item_write_permission(self):
        """Test if write permission is checked correctly."""
        user = "a"
        item_abort = {'_id': 'b'}
        item_pass = {'_id': user}

        with self._init_context(current_user=user, auth_required=True):
            # Abort(403) will raise the "Forbidden" exception
            with self.assertRaises(Forbidden):
                check_item_write_permission('fake', item_abort)

            # If the auth class returns true it wont be aborted, no exception
            check_item_write_permission('fake', item_pass)

    def test_resource_write_permission(self):
        """Test if write permission is checked correctly."""
        user = "somethingsomething"

        with self._init_context(current_user=user, auth_required=True):
            # using AmivTokenAuth subclass
            # Abort(403) will raise the "Forbidden" exception
            with self.assertRaises(Forbidden):
                check_resource_write_permission('fake')

            # If the auth class returns true it wont be aborted, no exception
            g.current_user = 'allowed'
            check_resource_write_permission('fake')

    # Tests for `abort_if_not_public`

    def test_abort_if_not_public(self):
        """Test that if g.requires_auth has an effect.

        If it is True and no user is there (and no admin) then it will abort.
        """
        with self._init_context():
            # user is None by default, admin is False
            # g.auth_required not set (e.g. no amivauth subclass) -> nothing
            abort_if_not_public()

            # Set to False -> nothing
            g.auth_required = False
            abort_if_not_public()

            # Set to True -> abort(401)/Forbidden
            g.auth_required = True
            with self.assertRaises(Unauthorized):
                abort_if_not_public()

            # User was found -> no abort
            g.current_user = "something"
            abort_if_not_public()

    # Tests for authentication

    def test_authentication_defaults(self):
        """Make sure authenticate sets defaults for all auth values."""
        expect_none = 'current_token', 'current_user', 'current_session'
        expect_false = 'resource_admin', 'resource_admin_readonly'

        with self.app.test_request_context():
            # Nothing there before
            for item in expect_none + expect_false:
                with self.assertRaises(AttributeError):
                    getattr(g, item)

            authenticate()
            for item in expect_none:
                self.assertIsNone(getattr(g, item))

            check_if_admin('someresource')
            for item in expect_false:
                self.assertFalse(getattr(g, item))

    def test_token_parsing_in_authentication(self):
        """Test all possible ways to send a token.

        1. As Basic Authorization header with token as user and no password
        2. As Authorization Header: 'Token <token>' (also lowercase)
        3. A Authorization Header: 'Bearer <token>' (also lowercase)
        4. Authorization header with only 'token'

        Also test that no or incomplete auth header results in
        `g.current_token = None`
        """
        # No Header
        with self.app.test_request_context():
            authenticate()
            self.assertIsNone(g.current_token)

        token = "ThisIsATokenYeahItIsTheContentDoesntReallyMatter"
        # Encoding dance for py 2/3 compatibility
        b64token = b64encode((token + ":").encode('utf-8')).decode('utf-8')

        # Header variations
        for header in (
                token,
                "Token " + token,
                "Bearer " + token,
                "SomeotherKeyword " + token,
                "Basic " + b64token):

            with self.app.test_request_context(
                    headers={'Authorization': header}):
                # Call authenticate, the token should be found and put in g
                authenticate()
                self.assertEqual(g.current_token, token)

    def test_session_lookup_in_authentication(self):
        """Test that sessions associated with a token are found correctly.

        If there is no session, `current_session` and `current_user` will be
        None, otherwise `current_session` will be the data as stored in the db
        and `current_user` the `user` field taken from the session.

        Also check that if a session is found the timestamp is updated
        """
        collection = self.db['sessions']
        # Provide everything for mongo, doesn't matter that we are not using
        # proper ObjectIds
        data = [
            {u'_id': u'a',
             u'user': ObjectId(24 * 'a'),
             u'token': u'sometoken',
             u'_updated': dt.now(timezone.utc) - timedelta(seconds=1)},
            {u'_id': u'b',
             u'user': ObjectId(24 * 'b'),
             u'token': u'othertoken',
             u'_updated': dt.now(timezone.utc) - timedelta(seconds=1)}
        ]

        # Put into db
        collection.insert_many(data)

        for session in data:
            with self.app.test_request_context(
                    headers={'Authorization': session['token']}):
                authenticate()

                # g.current_user shoudl be a string
                expected_user = str(session['user'])

                # TODO
                # session_in_db = \
                #    self.db['sessions'].find_one({'_id': session['_id']})
                # self.assertEqual(g.current_session, session_in_db)

                for key in '_id', 'user', 'token':
                    self.assertEqual(g.current_session[key], session[key])
                self.assertEqual(g.current_user, expected_user)
                self.assertGreater(g.current_session['_updated'],
                                   session['_updated'])

    def test_admin_rights_for_root(self):
        """Test that login with root sets `g.resource_admin` to True.

        Login with root means that the token is the root password.
        """
        root_pw = self.app.config['ROOT_PASSWORD']
        with self._init_context(current_token=root_pw):
            check_if_admin('some_resource')
            self.assertTrue(g.resource_admin)

    def test_auth_hook(self):
        """Assert that a auth hook is called and can set admin."""
        def test_hook(resource):
            if resource == "admin_resource":
                g.resource_admin = True
            else:
                g.resource_admin = False

        self.app.after_auth += test_hook

        with self.app.app_context():
            check_if_admin('something')
            self.assertFalse(g.resource_admin)

            check_if_admin('admin_resource')
            self.assertTrue(g.resource_admin)
