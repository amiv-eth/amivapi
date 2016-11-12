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

from amivapi.tests.utils import WebTest
from amivapi.ldap import ldap_connector


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

        self.assertTrue(
            all(self.data.values()),
            "Some environment variables are missing!")

        # Python2 fix: Make everything unicode
        for key, value in self.data.items():
            if type(value) is bytes:
                self.data[key] = value.decode("utf-8")

    def test_escape(self):
        """Test proper escaping of all characters."""
        to_escape = "*()\\" + chr(0)
        expected = r"\\2A\\28\\29\\5C\\00"

        self.assertEqual(ldap_connector._escape(to_escape), expected)

    def test_authenticate_user(self):
        """Assert authentication is successful."""
        with self.app.app_context():
            self.assertTrue(
                ldap_connector.authenticate_user(
                    self.data['nethz'], self.password)
            )

    def test_find_user(self):
        """Assert user can be found and data is correct.

        Note: This also means that a password is not in the ldap data.
        (Which is nice, since we don't want to store that.)
        """
        with self.app.app_context():
            user = ldap_connector.find_user(self.data['nethz'])
            self.assertIsNotNone(user)
            self.assertEqual(user, self.data)

    def test_find_members(self):
        """Assert that find_members works.

        - All imported users are members
        - Our user is in the list.
        """
        with self.app.app_context():
            members = list(ldap_connector.find_members())

            # Assert something is found
            self.assertTrue(members)

            # Assert only members are imported
            everyone_is_member = all(member['membership'] == 'regular'
                                     for member in members)

            self.assertTrue(everyone_is_member)

            # Assert user is found
            user_data = [member for member in members
                         if member['nethz'] == self.data['nethz']]
            self.assertEqual(user_data, self.data)

    def test_compare_and_update(self):
        """Assert that compare_and_update only changes necessary fields."""
        fixtures = self.load_fixture({
            'users': [{'firstname': u'db', 'lastname': u'db'}]})
        user_id = fixtures[0]['_id']

        with self.app.test_request_context():
            # Fake db data, only firstname should change
            fake_db_data = {'_id': user_id,
                            'firstname': 'db',
                            'lastname': 'ldap'}
            fake_ldap_data = {'firstname': 'ldap',
                              'lastname': 'ldap'}

            ldap_connector.compare_and_update(fake_db_data, fake_ldap_data)

            # Get user from database and compare
            user = self.db['users'].find_one({'_id': user_id})
            self.assertEqual(user['firstname'], 'ldap')
            self.assertEqual(user['lastname'], 'db')

    def test_update_only_upgrades_membership(self):
        """Assert that the update only changes membership if none."""
        data_no_change = {'_id': 24 * '0',
                          'nethz': 'nochange', 'membership': u"honorary"}
        data_change = {'_id': 24 * '1',
                       'nethz': 'change', 'membership': u"none"}
        self.load_fixture({'users': [data_no_change, data_change]})

        with self.app.test_request_context():
            ldap_data = {'membership': u'regular'}

            ldap_connector.compare_and_update(data_no_change, ldap_data)
            ldap_connector.compare_and_update(data_change, ldap_data)

            user_no_change = self.db['users'].find_one({'nethz': 'nochange'})
            user_change = self.db['users'].find_one({'nethz': 'change'})
            self.assertEqual(user_no_change['membership'],
                             data_no_change['membership'])
            self.assertEqual(user_change['membership'],
                             ldap_data['membership'])

    def test_update_doesnt_change_email(self):
        """Assert that mail is never changed."""
        data_no_change = {'nethz': 'nochange', 'email': u"any@thing.ch"}
        self.load_fixture({'users': [data_no_change]})

        with self.app.test_request_context():
            ldap_data = {'email': u'some@thing.ch'}

            ldap_connector.compare_and_update(data_no_change, ldap_data)

            user_no_change = self.db['users'].find_one({'nethz': 'nochange'})
            self.assertEqual(user_no_change['email'],
                             data_no_change['email'])

    def test_sync_one_import(self):
        """Assert synchronizing one user works."""
        with self.app.test_request_context():
            user = ldap_connector.sync_one(self.data['nethz'])

            # Double check with database
            check_user = self.db['users'].find_one(
                {'nethz': self.data['nethz']})

            # Compare by key since self.data doesnt have fields with _
            for key in self.data:
                self.assertEqual(user[key], self.data[key])
                self.assertEqual(check_user[key], self.data[key])

    def test_sync_one_update(self):
        """Same as before, but the user exists now before ldap sync."""
        self.load_fixture({'users': [{'nethz': self.data['nethz'],
                                      'membership': u"none"}]})

        with self.app.test_request_context():
            user = ldap_connector.sync_one(self.data['nethz'])

            # Double check with database
            check_user = self.db['users'].find_one(
                {'nethz': self.data['nethz']})

            # Compare by key since self.data doesnt have fields with
            # email won't be changed, so don't check that
            keys_except_mail = (key for key in self.data if key != "email")
            for key in keys_except_mail:
                self.assertEqual(user[key], self.data[key])
                self.assertEqual(check_user[key], self.data[key])

    def test_sync_all(self):
        """Test sync all imports users by checking the test user."""
        with self.app.test_request_context():
            ldap_connector.sync_all()

            # Find test user
            user = self.db['users'].find_one({'nethz': self.data['nethz']})

            for key in self.data:
                self.assertEqual(user[key], self.data[key])

    def test_sync_all_update(self):
        """Same as before, but the user exists now before ldap sync."""
        self.load_fixture({'users': [{'nethz': self.data['nethz'],
                                      'membership': u"none"}]})

        with self.app.test_request_context():
            ldap_connector.sync_all()

            # Find test user
            user = self.db['users'].find_one({'nethz': self.data['nethz']})

            # email won't be changed, so don't check that
            keys_except_mail = (key for key in self.data if key != "email")
            for key in keys_except_mail:
                self.assertEqual(user[key], self.data[key])

    def test_import_on_login(self):
        """Test that login imports the user."""
        data = {'username': self.data['nethz'], 'password': self.password}
        self.api.post("/sessions", data=data, status_code=201)

        user = self.db['users'].find_one({'nethz': self.data['nethz']})
        self.assertIsNotNone(user)

    def test_update_on_login(self):
        """Test login again, but this time the user already exists."""
        self.load_fixture({'users': [{'nethz': self.data['nethz'],
                                      'membership': u"none"}]})

        data = {'username': self.data['nethz'], 'password': self.password}
        self.api.post("/sessions", data=data, status_code=201)

        # Comparison necessary to make sure it was updated
        # email won't be changed, so don't check that
        user = self.db['users'].find_one({'nethz': self.data['nethz']})
        keys_except_mail = (key for key in self.data if key != "email")
        for key in keys_except_mail:
            self.assertEqual(user[key], self.data[key])
