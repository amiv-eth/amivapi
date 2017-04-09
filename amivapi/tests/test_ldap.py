# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""LDAP Tests.

Mock the actual ldap responses, since we can only access ldap in the eth
network which is not usually possible for testing, e.g. on travis.

There is another file, "ldap_integration.py", which can be used to test
integration with the real ldap. More info there.
"""

from unittest.mock import MagicMock, patch

from amivapi import ldap
from amivapi.tests.utils import WebTest, WebTestNoAuth

MOCK_LDAP_DATA = {
    'testuser1': {
        'password': 'testpass1',

    },
    'testuser2': {
        'password': 'testpass2',

    }
}

EXPECTED_RESULTS = {
    'testuser1': {

    },
    'testuser2': {

    },

}


class LdapAuthTest(WebTest):
    """Tests for LDAP auth."""

    def setUp(self, *args, **kwargs):
        """Extended setUp, enable LDAP and replace it with a Mock object."""
        self.test_config['ENABLE_LDAP'] = True
        self.test_config['LDAP_USER'] = self.test_config['LDAP_PASS'] = "Bla."
        self.mock_ldap = MagicMock()
        # When instantiated, it will return the mock object to use in the tests
        ldap.AuthenticatedLdap = MagicMock(return_value=self.mock_ldap)
        super(LdapAuthTest, self).setUp(*args, **kwargs)

    def test_ldap_auth(self):
        """Test that ldap can authenticate a user."""
        # Auth without ldap doesnt succeed
        self.mock_ldap.authenticate = MagicMock(return_value=False)
        self.api.post("/sessions",
                      data={'username': 'Pablo', 'password': 'p4bl0'},
                      status_code=401)

        self.mock_ldap.authenticate = MagicMock(return_value=True)

        # We patch sync one to return an existing user
        # sync one is tested separately
        sync = 'amivapi.ldap.LdapConnector.sync_one'
        _id = {'_id': self.new_object('users')["_id"]}
        with patch(sync, return_value=_id) as patched_sync:
            # Auth with ldap succeeds
            self.api.post("/sessions",
                          data={'username': 'Pablo', 'password': 'p4bl0'},
                          status_code=201)

            # But we will assert that sync_one is called for successful auth
            patched_sync.assert_called()


class LdapTest(WebTestNoAuth):
    """Tests for various LDAP functions like sync."""

    def test_escape(self):
        """Test proper escaping of all characters."""
        to_escape = "*()\\" + chr(0)
        expected = r"\\2A\\28\\29\\5C\\00"

        self.assertEqual(ldap._escape(to_escape), expected)


    def test_filter(self):
        """The received LDAP data can look weird. Test that it is filtered."""
        ldap_data = {
            'cn': ['pablo'],
            'swissEduPersonMatriculationNumber': '01234567',
            'givenName': ['P'],
            'sn': ['Ablo'],
            'swissEduPersonGender': '0',
            'ou': ['VSETH Mitglied', 'D-ITET',
                   'Informationstechnologie und Elektrotechnik'],
            'some_random_field': 'abc',
        }

        with self.app.app_context():
            filtered = ldap._filter_data(ldap_data)

        expected = {
            'nethz': 'pablo',
            'firstname': 'P',
            'lastname': 'Ablo',
            'department': 'itet',
            'membership': 'regular'
        }

        self.assertEqual(filtered, expected)

'''

# No Pablo in database yet
        token = self.get_root_token()
        self.api.get('/users/pablo', status_code=404, token=token)

        # We need to be able to find, authenticate and sync the user
        ldap_user = {
            'cn': ['pablo'],
            'swissEduPersonMatriculationNumber': '01234567',
            'givenName': ['P'],
            'sn': ['Ablo'],
            'swissEduPersonGender': '0',
            'ou': ['VSETH Mitglied']
        }

        self.mock_ldap.search = Mock(return_value=[ldap_user])




    def setUp(self, *args, **kwargs):
        """Extended setUp, replace the ldap in ldap_connector.
        """
        self.test_config['ENABLE_LDAP'] = True
        ldap_connector.ldap = MockLdap()

        super(LdapTest, self).setUp(*args, **kwargs)



    def test_authenticate_user(self):
        """Assert authentication is successful."""
        with self.app.app_context():
            self.assertTrue(
                ldap_connector.authenticate_user('testuser1', 'testpass1'))

    def test_find_user(self):
        """Assert user can be found."""
        with self.app.app_context():
            user = ldap_connector.find_user('testuser1')
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
'''
