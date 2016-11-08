# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test that additional fields are projected for events. These are:
- events.signup_count
- eventsignups.email
- eventsignups.confirmed
- eventsignups.position
"""

from amivapi.tests.utils import WebTestNoAuth
from freezegun import freeze_time
from datetime import timedelta


class EventProjectionTest(WebTestNoAuth):
    def test_signup_count_projected(self):
        """Test that signup count is correctly inserted into an event"""
        event = self.new_object('events', spots=100)

        # Add 10 signups
        self.load_fixture({'users': [{} for _ in range(10)],
                           'eventsignups': [{} for _ in range(10)]})

        event = self.api.get('/events/%s' % event['_id'], status_code=200).json
        self.assertEqual(event['signup_count'], 10)

        # Test for collection
        events = self.api.get('/events', status_code=200).json
        self.assertEqual(events['_items'][0]['signup_count'], 10)

    def test_waitinglist_position_projection(self):
        """Test that waiting list position is correctly inserted into a
        signup information"""
        with freeze_time("2016-01-01 00:00:00") as frozen_time:
            # Create a new event
            event = self.new_object('events', spots=3)

            # Add 3 signups
            for _ in range(3):
                user = self.new_object('users')
                self.api.post('/eventsignups', data={
                    'event': str(event['_id']),
                    'user': str(user['_id'])
                }, status_code=201)
                frozen_time.tick(delta=timedelta(seconds=1))

            # Check that the number of signups on that event is correct
            event = self.api.get('events/%s' % event['_id'],
                                 status_code=200).json
            self.assertTrue(event['signup_count'] == 3)

            # Delay signup of late user
            frozen_time.tick(delta=timedelta(seconds=1))

            late_user = self.new_object('users')
            signup = self.api.post('/eventsignups', data={
                'event': str(event['_id']),
                'user': str(late_user['_id'])
            }, status_code=201).json

            # GET the late user's signup to check his position
            signup_info = self.api.get(
                'eventsignups/%s' % signup['_id'],
                status_code=200).json
            self.assertEqual(signup_info['position'], 4)

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

        # Test for collection
        signups = self.api.get('/eventsignups', status_code=200).json
        self.assertEqual(signups['_items'][0]['confirmed'], False)
