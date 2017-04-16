# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Integration Tests for LDAP.

The API can connect to ETH LDAP to process login and update user data.

Since we don't have access to test accounts for LDAP you need to provide
valid ETH data for the tests to work.

This means we need lots of environment variables:
- ldap_nethz
- ldap_password
- ldap_firstname
- ldap_lastname
- ldap_legi
- ldap_gender
- ldap_department
- ldap_membership

If you are unsure how to set environment variables:
Bash:
> export ldap_test_nethz="YOUR_NETHZ"

Windows PowerShell:
> $env:ldap_test_nethz="YOUR_NETHZ_HERE"

Note: If you want to run the tests a lot, it might be best to create a script
that sets all those variables for you. Also: If you know a better way to do
this, please tell me ;)

Furthermore make sure the config.cfg contains:

LDAP_USER = 'YOUR_LDAP_ACCOUNT'
LDAP_PASS = 'YOUR_LDAP_ACCOUNT_PASSWORD'
"""

from os import getenv

from amivapi import ldap
from amivapi.tests.utils import WebTest


class LdapIntegrationTest(WebTest):
    """Tests for LDAP connection."""

    def setUp(self, *args, **kwargs):
        """Extended setUp.

        Load environment variables and test general ldap connection.
        """
        self.test_config['ENABLE_LDAP'] = True
        super(LdapIntegrationTest, self).setUp(*args, **kwargs)
        self.data = {
            'nethz': getenv('ldap_nethz'),
            'firstname': getenv('ldap_firstname'),
            'lastname': getenv('ldap_lastname'),
            'legi': getenv('ldap_legi'),
            'gender': getenv('ldap_gender'),
            'department': getenv('ldap_department'),
            'membership': getenv('ldap_membership')
        }
        self.data['email'] = "%s@ethz.ch" % self.data['nethz']
        self.password = getenv('ldap_password')
        # Python2 fix: Make everything unicode
        for key, value in self.data.items():
            if type(value) is bytes:
                self.data[key] = value.decode("utf-8")

    def test_variables(self):
        """Assert all environment variables are set."""
        self.assertTrue(
            all(self.data.values()),
            "Some environment variables are missing!")

    def test_login(self):
        """Test that post to sessions works."""
        credentials = {'username': self.data['nethz'],
                       'password': self.password}
        self.api.post('/sessions', data=credentials, status_code=201)

    def test_authenticate_user(self):
        """Assert authentication is successful."""
        with self.app.app_context():
            self.assertTrue(
                ldap.authenticate_user(
                    self.data['nethz'], self.password)
            )

    def test_sync_one(self):
        """Assert synchronizing one user works."""
        with self.app.test_request_context():
            user = ldap.sync_one(self.data['nethz'])

            # Double check with database
            check_user = self.db['users'].find_one(
                {'nethz': self.data['nethz']})

            # Compare by key since self.data doesnt have fields with _
            for key in self.data:
                self.assertEqual(user[key], self.data[key])
                self.assertEqual(check_user[key], self.data[key])

    def test_sync_all(self):
        """Test sync all imports users by checking the test user."""
        with self.app.test_request_context():
            ldap.sync_all()

            # Find test user
            user = self.db['users'].find_one({'nethz': self.data['nethz']})

            for key in self.data:
                self.assertEqual(user[key], self.data[key])
