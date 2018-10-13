# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for subscriberlist module.

Checks if authorization works and if the correct value is returned.
"""

from base64 import b64encode

from amivapi.tests import utils


class SubscriberlistTest(utils.WebTestNoAuth):
    """Basic tests for subscriber list resource."""

    def setUp(self):
        """Set username and password to enable subscriberlist endpoint."""
        super().setUp(SUBSCRIBER_LIST_USERNAME='test',
                      SUBSCRIBER_LIST_PASSWORD='test')
        basicauth = b64encode(b'test:test').decode('utf-8')
        self.auth_header = {'Authorization': 'Basic %s' % basicauth}

    def test_subscriberlist_response(self):
        entries = [
            {
                'nethz': 'pablamiv',
                'firstname': "Pabla",
                'lastname': "AMIV",
                'membership': "regular",
                'legi': "12345678",
                'gender': 'female',
                'department': 'itet',
                'password': "userpass",
                'email': "pabla@amiv.ch",
                'rfid': "123456",
                'send_newsletter': True
            },
            {
                'nethz': 'pablomiv',
                'firstname': "Pablo",
                'lastname': "AMIV",
                'membership': "regular",
                'legi': "87654321",
                'gender': 'male',
                'department': 'mavt',
                'password': "userpass2",
                'email': "pablo@amiv.ch",
                'rfid': "654321",
                'send_newsletter': True
            },
            {
                'nethz': 'pablemiv',
                'firstname': "Pable",
                'lastname': "AMIV",
                'membership': "regular",
                'legi': "87654329",
                'gender': 'male',
                'department': 'itet',
                'password': "userpass3",
                'email': "pable@amiv.ch",
                'rfid': "654323"
            }
        ]

        self.load_fixture({
            'users': entries
        })

        # expected = 'pabla@amiv.ch\tPabla AMIV\npablo@amiv.ch\tPablo AMIV\n'
        expected = ''
        for u in entries:
            if 'send_newsletter' in u and u['send_newsletter']:
                expected += ('%s %s %s\n' %
                             (u['email'], u['firstname'], u['lastname']))

        response = self.api.get('/newslettersubscribers',
                                headers=self.auth_header,
                                status_code=200).get_data(as_text=True)

        self.assertEqual(response, expected)

    def test_subscriberlist_auth(self):
        """Test that authorization is required."""
        self.api.get('/newslettersubscribers', status_code=401)

        wrong_auth = {'Authorization': "Basic 1234"}
        self.api.get('/newslettersubscribers', headers=wrong_auth,
                     status_code=401)

        self.api.get('/newslettersubscribers', headers=self.auth_header,
                     status_code=200)
