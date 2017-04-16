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

from mock import MagicMock, patch, call

from amivapi import ldap
from amivapi.tests.utils import WebTestNoAuth


class LdapTest(WebTestNoAuth):
    """Tests for LDAP with a mock connection."""

    def setUp(self, *args, **kwargs):
        """Extended setUp, enable LDAP and replace it with a Mock object."""
        super(LdapTest, self).setUp(*args, **kwargs)

        self.app.config['ENABLE_LDAP'] = True
        self.mock_ldap = self.app.config['ldap_connector'] = MagicMock()

    def test_init_app(self):
        """Test that init app uses correct credentials stored connector."""
        self.app.config['LDAP_USER'] = 'test'
        self.app.config['LDAP_PASS'] = 'T3ST'
        to_patch = 'amivapi.ldap.AuthenticatedLdap'
        with patch(to_patch, return_value='initialized') as init:
            ldap.init_app(self.app)

            init.assert_called_with('test', 'T3ST')
            self.assertEqual(self.app.config['ldap_connector'], 'initialized')

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
        sync = 'amivapi.ldap.sync_one'
        _id = {'_id': self.new_object('users')["_id"]}
        with patch(sync, return_value=_id) as patched_sync:
            # Auth with ldap succeeds
            self.api.post("/sessions",
                          data={'username': 'Pablo', 'password': 'p4bl0'},
                          status_code=201)

            # But we will assert that sync_one is called for successful auth
            patched_sync.assert_called()

    def test_escape(self):
        """Test proper escaping of all characters."""
        to_escape = "thisisok*()\\" + chr(0)
        expected = r"thisisok\\2A\\28\\29\\5C\\00"

        self.assertEqual(ldap._escape(to_escape), expected)

    def fake_ldap_data(self, **kwargs):
        """Produce basic fake ldap data to test filter."""
        data = {
            'cn': ['pablo'],
            'swissEduPersonMatriculationNumber': '01234567',
            'givenName': ['P'],
            'sn': ['Ablo'],
            'swissEduPersonGender': '0',
            'ou': ['VSETH Mitglied', 'D-ITET',
                   'Informationstechnologie und Elektrotechnik'],
            'some_random_field': 'abc',
        }
        data.update(kwargs)
        return data

    def fake_filtered_data(self):
        """Some data that is a valid output of _filter_data."""
        return {
            'nethz': 'pablo',
            'email': 'pablo@ethz.ch',  # this will be auto-generated
            'firstname': 'P',
            'lastname': 'Ablo',
            'department': 'itet',
            'membership': 'regular',
            'gender': 'female',
            'legi': '01234567'
        }

    def test_filter_data(self):
        """The received LDAP data can look weird. Test that it is filtered."""
        with self.app.app_context():
            filtered = ldap._filter_data(self.fake_ldap_data())
            expected = self.fake_filtered_data()

            self.assertEqual(filtered, expected)

    def test_filter_gender(self):
        """ Test parsing of gender field."""
        with self.app.app_context():
            female_data = self.fake_ldap_data(swissEduPersonGender='0')
            female_filtered = ldap._filter_data(female_data)
            self.assertTrue(female_filtered['gender'] == 'female')

            male_data = self.fake_ldap_data(swissEduPersonGender='1')
            male_filtered = ldap._filter_data(male_data)
            self.assertTrue(male_filtered['gender'] == 'male')

    def test_filter_department(self):
        """Test deparment filtering. The 'ou' entry has to be checked."""
        with self.app.app_context():
            tests = (
                ('D-ITET', 'itet'),
                ('D-MAVT', 'mavt'),
                ('D-Somethingelse', 'other')
            )
            for ldap_value, api_value in tests:
                data = self.fake_ldap_data(ou=[ldap_value])
                filtered = ldap._filter_data(data)
                self.assertTrue(filtered['department'] == api_value)

    def test_filter_membership(self):
        """Test membership filtering. The 'ou' entry has to be checked."""
        with self.app.app_context():
            # ou must contain 'VSETH Mitglied' and any of the specified 'ou'
            # values
            self.app.config['LDAP_MEMBER_OU_LIST'] = [
                'test_value', 'other_value'
            ]

            tests = (
                # (ou, expected result)
                (['VSETH Mitglied', 'test_value'], 'regular'),
                (['VSETH Mitglied', 'other_value'], 'regular'),
                # Something missing
                (['VSETH Mitglied'], 'none'),
                (['test_value'], 'none'),
                (['other_value'], 'none'),
                ([], 'none'),
            )

            for (ou_values, result) in tests:
                data = self.fake_ldap_data(ou=ou_values)
                filtered = ldap._filter_data(data)
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
            'ou'
            ]
        mock_results = [1, 2, 3]
        # Mock ldap query

        mock_search = MagicMock(return_value=mock_results)
        self.app.config['ldap_connector'].search = mock_search
        # Mock _filter_data to check results
        with patch('amivapi.ldap._filter_data') as mock_filter:
            with self.app.app_context():
                result = ldap._search(test_query)

                # Verify correct query
                mock_search.assert_called_with(test_query, attributes=attr)

                # Assert _filter_data is called with ldap results
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
        """Test if sync_all contructs the query correctly and creates users."""
        # Make ou list shorter
        self.app.config['LDAP_MEMBER_OU_LIST'] = ['a', 'b']
        expected_query = '(& (ou=VSETH Mitglied) (| (ou=a)(ou=b)) )'
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
