# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""LDAP Tests.

Mock the actual ldap responses, since we can only access ldap in the ETH
network which is not usually possible for testing, e.g. on travis.

There is another file, "ldap_integration.py", which can be used to test
integration with the real ldap. More info there.
"""

from unittest.mock import MagicMock, patch, call
import warnings

from os import getenv
from pprint import pformat

from amivapi import ldap
from amivapi.tests.utils import WebTest, WebTestNoAuth, skip_if_false


class LdapTest(WebTestNoAuth):
    """Tests for LDAP with a mock connection."""

    def setUp(self, *args, **kwargs):
        """Extended setUp, enable LDAP and replace it with a Mock object."""
        super(LdapTest, self).setUp(*args, **kwargs)

        self.app.config['ENABLE_LDAP'] = True
        self.mock_ldap = self.app.config['ldap_connector'] = MagicMock()

    def test_init_app(self):
        """Test that init app uses correct credentials stored connector."""
        ldap_user = 'test'
        ldap_pass = 'T3ST'
        initialized_ldap = 'I totally am an ldap instance.'

        self.app.config['LDAP_USERNAME'] = ldap_user
        self.app.config['LDAP_PASSWORD'] = ldap_pass
        to_patch = 'amivapi.ldap.AuthenticatedLdap'

        with patch(to_patch, return_value=initialized_ldap) as init:
            ldap.init_app(self.app)

            init.assert_called_with(ldap_user, ldap_pass)
            self.assertEqual(self.app.config['ldap_connector'],
                             initialized_ldap)

    def test_ldap_auth(self):
        """Test that ldap can authenticate a user."""
        nethz = "Pablo"
        login_data = {'username': nethz, 'password': 'p4bl0'}
        # Auth without ldap doesnt succeed
        self.mock_ldap.authenticate = MagicMock(return_value=False)
        self.api.post("/sessions", data=login_data, status_code=401)

        # Auth with ldap succeeds
        self.mock_ldap.authenticate = MagicMock(return_value=True)
        # We patch sync one to return an existing user
        # sync one is tested separately
        sync = 'amivapi.ldap.sync_one'
        _id = {'_id': self.new_object('users')["_id"]}
        with patch(sync, return_value=_id) as patched_sync:
            self.api.post("/sessions", data=login_data, status_code=201)

            # But we will assert that sync_one is called for successful auth
            patched_sync.assert_called_with(nethz)

    def test_escape(self):
        """Test proper escaping of all characters."""
        to_escape = "thisisok*()\\" + chr(0)
        expected = r"thisisok\2A\28\29\5C\00"

        self.assertEqual(ldap._escape(to_escape), expected)

    def fake_ldap_data(self, **kwargs):
        """Produce basic fake ldap data to test filter."""
        data = {
            'cn': ['pablo'],
            'departmentNumber': ['ETH Studentin D-ITET, SomeFieldOfStudy M'],
            'swissEduPersonMatriculationNumber': '01234567',
            'givenName': ['P'],
            'sn': ['Ablo'],
            'swissEduPersonGender': '0',
            'ou': ['VSETH Mitglied', 'other unrelated entry'],
            'some_random_field': 'abc',
        }
        data.update(kwargs)
        return data

    def fake_filtered_data(self):
        """Some data that is a valid output of _process_data."""
        return {
            'nethz': 'pablo',
            'email': 'pablo@ethz.ch',  # this will be auto-generated
            'firstname': 'P',
            'lastname': 'Ablo',
            'department': 'itet',
            'membership': 'regular',
            'gender': 'female',
            'legi': '01234567',
            'send_newsletter': True,
        }

    def test_process_data(self):
        """The received LDAP data can look weird. Test that it is filtered."""
        with self.app.app_context():
            filtered = ldap._process_data(self.fake_ldap_data())
            expected = self.fake_filtered_data()

            self.assertEqual(filtered, expected)

    def test_process_gender(self):
        """ Test parsing of gender field."""
        with self.app.app_context():
            female_data = self.fake_ldap_data(swissEduPersonGender='0')
            female_filtered = ldap._process_data(female_data)
            self.assertTrue(female_filtered['gender'] == 'female')

            male_data = self.fake_ldap_data(swissEduPersonGender='1')
            male_filtered = ldap._process_data(male_data)
            self.assertTrue(male_filtered['gender'] == 'male')

    def test_process_department(self):
        """Test department filtering. Relies on 'departmentNUmber' field."""
        with self.app.app_context():
            tests = (
                ('ETH Studentin D-ITET', 'itet'),
                ('ETH Student D-ITET', 'itet'),
                ('ETH Student D-MAVT', 'mavt'),
                ('ETH Studentin D-MAVT', 'mavt'),
                ('ETH Student D-ITET and more text that', 'itet'),
                ('ETH Studentin D-SOMETHINGELSE', None),
                ('any other text', None),
                ('', None),
            )
            for ldap_value, api_value in tests:
                data = self.fake_ldap_data(departmentNumber=[ldap_value])
                filtered = ldap._process_data(data)
                self.assertTrue(filtered['department'] == api_value)

    def test_process_membership(self):
        """Test membership filtering."""
        with self.app.app_context():
            # ou must contain 'VSETH Mitglied'
            # and department must not be None (see other test)
            our = 'ETH Student D-ITET'
            other = 'ETH Student D-OTHER'
            self.app.config['LDAP_DEPARTMENT_MAP'] = {our: 'itet'}

            tests = (
                # (departmentNUmber, ou, expected result)
                ([our], ['VSETH Mitglied'], 'regular'),
                ([our], ['blabla', 'VSETH Mitglied', 'random'], 'regular'),
                # Something missing
                ([our], ['novseth'], 'none'),
                ([other], ['VSETH Mitglied'], 'none'),
                ([other], ['nonono'], 'none'),
                ([other], [], 'none'),
            )

            for (dn, ou, result) in tests:
                data = self.fake_ldap_data(departmentNumber=dn, ou=ou)
                filtered = ldap._process_data(data)
                self.assertTrue(filtered['membership'] == result)

    def test_create_user(self):
        """Test the 'create' part of _create_or_update_user."""
        new_user = self.fake_filtered_data()

        # User not found yet
        self.api.get('/users/%s' % new_user['nethz'], status_code=404)

        with self.app.test_request_context():
            ldap._create_or_update_user(new_user)

        # User exists now
        self.api.get('/users/%s' % new_user['nethz'], status_code=200)

    def test_update_user(self):
        """Test the 'patch' part of _create_or_patch_user."""
        # The user is in the database. Now change a few things and verify
        # patch with original data does the correct thing
        tests = (
            # (field, db_value, ldap_value, change_expected)
            ('firstname', 'old', 'new', True),
            ('lastname', 'old', 'new', True),
            ('department', 'mavt', 'itet', True),
            ('gender', 'male', 'female', True),
            ('legi', '76543210', '01234567', True),
            # Membership is only upgraded
            ('membership', 'none', 'regular', True),
            ('membership', 'regular', 'none', False),
            ('membership', 'honorary', 'regular', False),
            ('membership', 'honorary', 'none', False),
            ('membership', 'extraordinary', 'regular', False),
            ('membership', 'extraordinary', 'none', False),
            # email will not be changed
            ('email', 'old@mail.de', 'new@mail.de', False)
        )

        for ind, (field, db_value, ldap_value, change) in enumerate(tests):
            # Create a new user for every test
            self.new_object('users', nethz=str(ind), **{field: db_value})
            ldap_data = {'nethz': str(ind), field: ldap_value}

            with self.app.test_request_context():
                result = ldap._create_or_update_user(ldap_data)

            if change:
                self.assertEqual(result[field], ldap_value)
            else:
                self.assertEqual(result[field], db_value)

    def test_search(self):
        """Test that ldap is correctly queried."""
        test_query = "äüáíðáßðöó"
        attr = [
            'cn',
            'swissEduPersonMatriculationNumber',
            'givenName',
            'sn',
            'swissEduPersonGender',
            'departmentNumber',
            'ou'
        ]
        mock_results = [1, 2, 3]
        # Mock ldap query

        mock_search = MagicMock(return_value=mock_results)
        self.app.config['ldap_connector'].search = mock_search
        # Mock _process_data to check results
        with patch('amivapi.ldap._process_data') as mock_filter:
            with self.app.app_context():
                result = ldap._search(test_query)

                # Verify correct query
                mock_search.assert_called_with(test_query, attributes=attr)

                # Assert _process_data is called with ldap results
                for ind, _ in enumerate(result):
                    mock_filter.assert_called_with(mock_results[ind])

    def test_sync_one_found(self):
        """Sync one queries ldap and creates user."""
        search_results = (i for i in [1])  # Mock generator
        search = 'amivapi.ldap._search'
        create = 'amivapi.ldap._create_or_update_user'
        with patch(search, return_value=search_results) as mock_search:
            with patch(create, return_value=2) as mock_create:
                query = "Abcsdi123"
                result = ldap.sync_one(query)

                self.assertEqual(result, 2)
                mock_search.assert_called_with('(cn=%s)' % query)
                mock_create.assert_called_with(1)

    def test_sync_one_no_results(self):
        """Test if sync one return None if there are no results."""
        search_results = (i for i in [])  # Mock generator
        search = 'amivapi.ldap._search'
        create = 'amivapi.ldap._create_or_update_user'
        with patch(search, return_value=search_results):
            with patch(create) as mock_create:
                query = "query"
                result = ldap.sync_one(query)

                self.assertEqual(result, None)
                mock_create.assert_not_called()

    def test_sync_all(self):
        """Test if sync_all builds the query correctly and creates users."""
        # Shorten ou list
        self.app.config['LDAP_DEPARTMENT_MAP'] = {'a': 'itet'}
        expected_query = '(& (ou=VSETH Mitglied) (| (departmentNumber=*a*)) )'
        search_results = (i for i in [1, 2])
        search = 'amivapi.ldap._search'
        create = 'amivapi.ldap._create_or_update_user'

        with patch(search, return_value=search_results) as mock_search:
            with patch(create, return_value=3) as mock_create:
                with self.app.app_context():
                    result = ldap.sync_all()

                mock_search.assert_called_with(expected_query)
                mock_create.assert_has_calls([call(1), call(2)])
                self.assertEqual(result, [3, 3])


# Integration Tests

# Get data from environment
LDAP_USERNAME = getenv('LDAP_TEST_USERNAME')
LDAP_PASSWORD = getenv('LDAP_TEST_PASSWORD')
LDAP_USER_NETHZ = getenv('LDAP_TEST_USER_NETHZ')
LDAP_USER_PASSWORD = getenv('LDAP_TEST_USER_PASSWORD')

requires_credentials = skip_if_false(LDAP_USERNAME and LDAP_PASSWORD,
                                     "LDAP test requires environment "
                                     "variables 'LDAP_TEST_USERNAME' and "
                                     "'LDAP_TEST_PASSWORD")


class LdapIntegrationTest(WebTest):
    """Tests for LDAP connection."""

    def setUp(self, *args, **kwargs):
        """Extended setUp.

        Load environment variables and test general ldap connection.
        """
        extra_config = {
            'LDAP_USERNAME': LDAP_USERNAME,
            'LDAP_PASSWORD': LDAP_PASSWORD,
        }
        extra_config.update(kwargs)
        super(LdapIntegrationTest, self).setUp(*args, **extra_config)

    @requires_credentials
    @skip_if_false(LDAP_USER_NETHZ and LDAP_USER_PASSWORD,
                   "LDAP login test requires environment variables"
                   "'LDAP_TEST_USER_NETHZ' and 'LDAP_TEST_USER_PASSWORD'")
    def test_login(self):
        """Test that post to sessions works."""
        credentials = {'username': LDAP_USER_NETHZ,
                       'password': LDAP_USER_PASSWORD}
        self.api.post('/sessions', data=credentials, status_code=201)

    @requires_credentials
    @skip_if_false(LDAP_USER_NETHZ and LDAP_USER_PASSWORD,
                   "LDAP login test requires environment variables"
                   "'LDAP_TEST_USER_NETHZ' and 'LDAP_TEST_USER_PASSWORD'")
    def test_authenticate_user(self):
        """Assert authentication is successful."""
        with self.app.app_context():
            self.assertTrue(
                ldap.authenticate_user(LDAP_USER_NETHZ, LDAP_USER_PASSWORD)
            )

    @requires_credentials
    @skip_if_false(LDAP_USER_NETHZ,
                   "LDAP user test requires environment variable"
                   "'LDAP_TEST_USER_NETHZ'")
    def test_sync_one(self):
        """Assert synchronizing one user works."""
        with self.app.test_request_context():
            user = ldap.sync_one(LDAP_USER_NETHZ)
            data_only = {key: value for (key, value) in user.items()
                         if not key.startswith('_')}  # no meta fields

            # Double check with database
            db_user = self.db['users'].find_one({'nethz': LDAP_USER_NETHZ})

            # Compare with database (ignore meta fields)
            for key in data_only:
                self.assertEqual(user[key], db_user[key])

            # Display user data for manual verification

            message = 'Manual data check required:\n%s' % pformat(data_only)
            warnings.warn(UserWarning(message))

    @requires_credentials
    def test_sync_all(self):
        """Test sync all imports users by checking the test user."""
        with self.app.test_request_context():
            # No users in db
            self.assertEqual(self.db['users'].find().count(), 0)
            ldap.sync_all()
            # Some users in db
            self.assertNotEqual(self.db['users'].find().count(), 0)
