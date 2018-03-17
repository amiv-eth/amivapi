# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Auth test case with a fake auth class added."""

from contextlib import contextmanager

from eve.auth import BasicAuth
from flask import g

from amivapi.auth import AmivTokenAuth
from amivapi.tests.utils import WebTest


class FakeAuth(AmivTokenAuth):
    """Testing auth class that makes it easy to check results."""

    def create_user_lookup_filter(self, user_id):
        """Simple lookup."""
        return {'_id': user_id}

    def has_item_write_permission(self, user_id, item):
        """Return true if _id field equals user."""
        return user_id == item['_id']

    def has_resource_write_permission(self, user_id):
        """Return true if user has id 'allowed'."""
        return user_id == 'allowed'


class FakeAuthTest(WebTest):
    """Unittests for the auth functions with fake auth."""

    # Setup and Helper

    def setUp(self):
        """Setup with fake resources that have only auth.

        - AmivTokenAuth subclass for the resource 'fake'.
        - A 'BasicAuth' (from Eve) subclass for 'fake_no_amiv'
        - No auth at all for 'fake_nothing'

        """
        super().setUp()

        self.app.config['DOMAIN']['fake'] = {
            # Its important we use a instance and not the class
            # So we can compare it in some tests
            'authentication': FakeAuth(),
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
