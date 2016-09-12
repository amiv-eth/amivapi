# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for auth functions."""

from base64 import b64encode
from datetime import datetime, timedelta

from flask import g
from werkzeug.exceptions import Unauthorized, Forbidden

from amivapi.auth import (
    AmivTokenAuth,
    add_lookup_filter,
    check_write_permission,
    abort_if_not_public,
    authenticate,
    check_if_admin
)
from amivapi.tests.utils import WebTest
from .fake_auth import FakeAuthTest


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
        self.assertIsNone(auth.create_user_lookup_filter(None))

    def test_amiv_token_auth_has_write_permission(self):
        """Test default write permission. Should be False."""
        auth = AmivTokenAuth()
        self.assertFalse(auth.has_write_permission(None, None))


class AuthFunctionTest(FakeAuthTest):
    """Unittests for the auth functions."""

    # Tests for add_lookup_filter

    def test_lookup_added_for_amiv_auth(self):
        """Test if lookup filters are added if using AmivTokenAuth subclass."""
        user = 'does not matter'
        lookup = {}
        expected = {'$and': [{'_id': user}]}

        with self._init_context(current_user=user):
            # No changes for no auth or not amiv auth
            for resource in ['fake_no_amiv', 'fake_nothing']:
                add_lookup_filter(resource, None, lookup)
                self.assertEqual(lookup, {})

            # Filter added when using fake AmivTokenAuthSubclass
            add_lookup_filter('fake', None, lookup)
            self.assertEqual(lookup, expected)

    def test_added_lookup_doesnt_overwrite_existing_and(self):
        """Test that lookup filters are added to existing $and."""
        user = 'test'
        lookup = {'$and': ['already_here']}
        expected = {'$and': ['already_here', {'_id': user}]}

        with self._init_context(current_user=user):
            add_lookup_filter('fake', None, lookup)
            self.assertEqual(lookup, expected)

    def test_lookup_not_added_for_admins(self):
        """Test that admins can see everything."""
        lookup = {}
        for context in [
                {'resource_admin': True},
                {'resource_admin_readonly': True},
                {'resource_admin': True, 'resource_admin_readonly': True}]:
            with self._init_context(**context):
                # Call filter for 'fake' resource, lookup should not change
                add_lookup_filter('fake', None, lookup)
                self.assertEqual(lookup, {})

    # Tests for `check_write_permission`

    def test_write_permission_checked_for_amiv_auth(self):
        """Test if write permission is checked correctly."""
        user = "a"
        item_abort = {'_id': 'b'}
        item_pass = {'_id': user}

        with self._init_context(current_user=user):
            # using AmivTokenAuth subclass
            # Abort(403) will raise the "Forbidden" exception
            with self.assertRaises(Forbidden):
                check_write_permission('fake', item_abort)

            # If the auth class returns true it wont be aborted, no exception
            check_write_permission('fake', item_pass)

            # No Exceptions for resources using other auth either
            for resource in ['fake_no_amiv', 'fake_nothing']:
                check_write_permission(resource, item_abort)

    def test_write_permission_not_checked_for_admin(self):
        """Test that admins can change everything.

        But readonly admins can't.
        """
        # This will lead to abort (see test above)
        user = "a"
        item = {'_id': "b"}

        with self._init_context(resource_admin=True, current_user=user):
            # No exception, admin can write
            check_write_permission('fake', item)

            # Change to readonly admin, now it will abort
            g.resource_admin = False
            g.resource_admin_readonly = True
            with self.assertRaises(Forbidden):
                check_write_permission('fake', item)

    # Tests for `abort_if_not_public`

    def test_abort_if_not_public(self):
        """Test that if g.requires_auth has an effect.

        If it is True and no user is there (and no admin) then it will abort.

        We don't need to test different auth classes because only the
        AmivTokenAuth class will set g.auth_required
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

    def test_no_abort_for_admin(self):
        """Test that nothing will abort for admins.

        Even without user, things like API keys can provide authentication
        via resource_admin or resource_admin_readonly. Then it wont abort.
        """
        for context in [
                {'resource_admin': True},
                {'resource_admin_readonly': True},
                {'resource_admin': True, 'resource_admin_readonly': True}]:
            with self._init_context(auth_required=True, **context):
                # No abort even though user is None
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

        Also test that no auth header leads to `g.current_token = None`
        """
        # No Header
        with self.app.test_request_context():
            authenticate()
            self.assertIsNone(g.current_token)

        token = "ThisIsATokenYeahItIsTheContentDoesntReallyMatter"
        # Encoding dance for py 2/3 compatibility
        b64token = b64encode((token + ":").encode('utf-8')).decode('utf-8')

        # All header variations
        for header in (
                token,
                "token " + token,
                "Token " + token,
                "bearer " + token,
                "Bearer " + token,
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
        and `current_user` the `user_id` field taken from the session.

        Also check that if a session is found the timestamp is updated
        """
        collection = self.db['sessions']
        # Provide everything for mongo, doesn't matter that we are not using
        # proper ObjectIds
        data = [
            {u'_id': u'a',
             u'user_id': u'someuser',
             u'token': u'sometoken',
             u'_updated': datetime.utcnow() - timedelta(seconds=1)},
            {u'_id': u'b',
             u'user_id': u'otheruser',
             u'token': u'othertoken',
             u'_updated': datetime.utcnow() - timedelta(seconds=1)}
        ]

        # Put into db
        collection.insert(data)

        for session in data:
            with self.app.test_request_context(
                    headers={'Authorization': session['token']}):
                authenticate()

                session_in_db = \
                    self.db['sessions'].find_one({'_id': session['_id']})
                self.assertEqual(g.current_session, session_in_db)

                for key in '_id', 'user_id', 'token':
                    self.assertEqual(g.current_session[key], session[key])
                self.assertEqual(g.current_user, session['user_id'])

                # Normally Eve would deal with timezones for us,
                # here we have to remove the tzinfo to be able to compare the
                # time (everything is utc anyways)
                g.current_session['_updated'] = \
                    g.current_session['_updated'].replace(tzinfo=None)
                self.assertGreater(g.current_session['_updated'],
                                   session['_updated'])

    def test_admin_rights_for_root(self):
        """Test that login with root sets `g.resource_admin` to True."""
        root_id = str(self.app.config['ROOT_ID'])
        with self._init_context(current_user=root_id):
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
