# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test that additional fields are projected for events. These are:
- events.signup_count
- eventsignups.email
- eventsignups.confirmed
"""

from amivapi.tests.utils import WebTestNoAuth


class EventProjectionTest(WebTestNoAuth):
    def test_signup_count_projected(self):
        """Test that signup count is correctly inserted into an event"""
        event = self.new_object('events', spots=100)

        # Add 10 signups
        self.load_fixture({'users': [{} for _ in range(10)],
                           'eventsignups': [{} for _ in range(10)]})

        event = self.api.get('/events/%s' % event['_id'], status_code=200).json
        self.assertEqual(event['signup_count'], 10)

    def test_signup_email_correct(self):
        """Test that signups display the correct email address"""
        event = self.new_object('events', spots=100)
        user = self.new_object('users', email='testemail@amiv.com')
        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        signup = self.api.get('/eventsignups/%s' % signup['_id'],
                              status_code=200).json
        self.assertEqual(signup['email'], 'testemail@amiv.com')

    def test_confirmed_projected(self):
        """Test that an external signups gets the confirmed field"""
        event = self.new_object('events', spots=100, additional_fields=None,
                                allow_email_signup=True)
        signup = self.api.post('/eventsignups', data={
            'event': str(event['_id']),
            'email': 'bla@bla.bla'
        }, status_code=201).json

        signup = self.api.get('/eventsignups/%s' % signup['_id'],
                              status_code=200).json
        self.assertEqual(signup['confirmed'], False)
