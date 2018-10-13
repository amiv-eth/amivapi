# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for subscriberlist module.

Checks if authorization works and if the correct value is returned.
"""

from amivapi.tests import utils


class SubscriberlistTest(utils.WebTestNoAuth):
    """Basic tests for subscriber list resource."""

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

        users = self.load_fixture({
            'users': entries
        })

        # expected = 'pabla@amiv.ch\tPabla AMIV\npablo@amiv.ch\tPablo AMIV\n'
        expected = ''
        for u in entries:
            if 'send_newsletter' in u and u['send_newsletter']:
                expected += '%s\t%s %s\n'%(u['email'], u['firstname'], u['lastname'])

        headers = {'Authorization': 'Basic YW1pdmFwaTphbWl2YXBp'}
        response = self.api.get('subscriberlist', headers=headers, status_code=200).get_data(as_text=True)

        self.assertEqual(response, expected)


    def test_subscriberlist_auth(self):
        """Test that authorization works."""
        self.api.get('subscriberlist', status_code=401)

        headers = {'Authorization': 'Basic YW1pdmFwaTphbWl2YXBp'}
        self.api.get('subscriberlist', headers=headers, status_code=200)
