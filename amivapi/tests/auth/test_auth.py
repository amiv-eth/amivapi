# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for auth functions."""

from contextlib import contextmanager
from base64 import b64encode
from datetime import datetime, timedelta

from flask import g
from werkzeug.exceptions import Unauthorized, Forbidden
from eve.auth import BasicAuth

from amivapi.auth import (
    AmivTokenAuth,
    add_lookup_filter,
    check_write_permission,
    abort_if_not_public,
    authenticate,
)
from amivapi.tests import utils


class AmivTokenAuthTest(utils.WebTest):
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


class FakeAuth(AmivTokenAuth):
    """Testing auth class that makes it easy to check results."""

    def create_user_lookup_filter(self, user_id):
        """Simple lookup."""
        return {'_id': user_id}

    def has_write_permission(self, user_id, item):
        """Return true if _id field equals user."""
        return user_id == item['_id']


class AuthFunctionTest(utils.WebTest):
    """Unittests for the auth functions."""

    # Setup and Helper

    def setUp(self):
        """Setup with fake resources that have only auth.

        - AmivTokenAuth subclass for the resource 'fake'.
        - A 'BasicAuth' (from Eve) subclass for 'fake_no_amiv'
        - No auth at all for 'fake_nothing'

        """
        super(AuthFunctionTest, self).setUp()

        self.app.config['DOMAIN']['fake'] = {
            'authentication': FakeAuth,
            # some different methods for public and not public
            'resource_methods': ['GET', 'POST', 'DELETE'],
            'public_methods': ['GET', 'POST'],
            'item_methods': ['GET', 'PATCH', 'DELETE'],
            'public_item_methods': ['GET', 'PATCH']
        }

        self.app.config['DOMAIN']['fake_no_amiv'] = {
            'authentication': BasicAuth}

        self.app.config['DOMAIN']['fake_nothing'] = {
            'authentication': None}

    @contextmanager
    def _init_context(self, **g_updates):
        """Create an app context and fill g with values."""
        with self.app.app_context():
            # Defaults - no admins and nothing
            g.current_token = g.current_session = g.current_user = None
            g.resource_admin = g.resource_admin_readonly = False

            # Update g
            for key, value in g_updates.items():
                setattr(g, key, value)

            yield

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

            # Now they are set
            for item in expect_none:
                self.assertIsNone(getattr(g, item))
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

    def test_admin_rights_for_root_in_authentication(self):
        """Test that login with root sets `g.resource_admin` to True."""
        root_token = 'somethingsomethingsecurity'
        root_id = str(self.app.config['ROOT_ID'])

        # Put in session
        self.db['sessions'].insert({u'user_id': root_id, u'token': root_token})

        with self.app.test_request_context(
                headers={'Authorization': root_token}):
            authenticate()
            self.assertEqual(g.current_user, root_id)
            self.assertTrue(g.resource_admin)
