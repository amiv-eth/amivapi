# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for custom validation rules for groups.

Since this hook will be added for all requests (the after auth hook) and this
is tested for auth.py we only get get on resource level to test functionality.
"""
from flask import g

from amivapi.tests.utils import WebTest


class PermissionsTest(WebTest):
    """Test that a groupmembership grants correct permissions."""

    UID = 24 * '0'

    def assertBase(self, admin, admin_readonly):
        """Assert baseline"""
        with self.app.app_context():
            self.api.get('/groups', status_code=200,
                         token=self.get_user_token(self.UID))
            self.assertEqual(g.get('resource_admin'), admin)
            self.assertEqual(g.get('resource_admin_readonly'), admin_readonly)

    def assertNothing(self):
        """Assert admin and admin_readonly are false or not in g."""
        self.assertBase(False, False)

    def assertAdmin(self):
        """Assert admin is true."""
        self.assertBase(True, False)

    def assertAdminReadonly(self):
        """Assert admin and admin_readonly are false or not in g."""
        self.assertBase(False, True)

    def permission_fixture(self, permissions):
        """Create user, group with permissions and membership."""
        gid = 24 * '1'
        self.load_fixture({
            'users': [{'_id': self.UID}],
            'groups': [{'_id': gid, 'permissions': permissions}],
            'groupmemberships': [{'user': self.UID, 'group': gid}]
        })

    def test_other_permissions_have_no_influence(self):
        """Test that permissions for other resources have no influence."""
        self.permission_fixture({'sessions': 'read', 'users': 'readwrite'})
        self.assertNothing()

    def test_admin(self):
        """Test that 'readwrite' gives admin permissions."""
        self.permission_fixture({'groups': 'readwrite'})
        self.assertAdmin()

    def test_readonly(self):
        """Test that 'readwrite' gives admin permissions."""
        self.permission_fixture({'groups': 'read'})
        self.assertAdminReadonly()
