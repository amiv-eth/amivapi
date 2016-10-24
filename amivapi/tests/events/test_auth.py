# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test event authorization"""

from amivapi.tests.utils import WebTest


class EventAuthTest(WebTest):
    def test_signup_only_yourself(self):
        """Test that users can not sign up other people for events"""
        ev = self.new_object("events", spots=100)
        user1 = self.new_object("users")
        user2 = self.new_object("users")

        user1_token = self.get_user_token(user1['_id'])

        self.api.post('eventsignups',
                      data={'user': str(user1['_id']),
                            'event': str(ev['_id'])},
                      token=user1_token,
                      status_code=201)

        self.api.post('eventsignups',
                      data={'user': str(user2['_id']),
                            'event': str(ev['_id'])},
                      token=user1_token,
                      status_code=422)

    def test_see_only_own_signups(self):
        """Test that users can only see their own signups"""

        # Fill database with some data
        self.load_fixture({
            'users': [{} for _ in range(3)],
            'events': [{} for _ in range(3)],
            'eventsignups': [{} for _ in range(6)]
        })

        user = self.new_object('users')
        user_token = self.get_user_token(user['_id'])

        self.assertEqual(self.api.get('eventsignups', token=user_token,
                                      status_code=200).json['_meta']['total'],
                         0)

        self.new_object('eventsignups', user=user['_id'])

        self.assertEqual(self.api.get('eventsignups', token=user_token,
                                      status_code=200).json['_meta']['total'],
                         1)

    def test_externals_can_post(self):
        """Test that post is possible with email address without login"""
        event = self.new_object('events', additional_fields=None,
                                allow_email_signup=True)

        self.api.post('eventsignups', data={
            'event': str(event['_id']),
            'email': 'test@bla.com',
        }, status_code=201)
