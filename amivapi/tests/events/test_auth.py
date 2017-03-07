# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test event authorization"""

from datetime import datetime
from freezegun import freeze_time
import json

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

    def test_signups_patchable_fields(self):
        """Test that only additional_fields can be changes by users and accepted
        only by admins."""
        event = self.new_object(
            'events', spots=100, additional_fields=json.dumps({
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object",
                "additionalProperties": False,
                'properties': {'a': {}}}))
        event2 = self.new_object(
            'events', spots=100, additional_fields=json.dumps({
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object",
                "additionalProperties": False,
                'properties': {'a': {}}}))

        user = self.new_object('users')
        user2 = self.new_object('users')
        user_token = self.get_user_token(user['_id'])
        root_token = self.get_root_token()

        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id']),
            'additional_fields': '{"a": 1}'
        }, token=root_token, status_code=201).json

        # Check that user can not be patched
        self.api.patch('/eventsignups/%s' % signup['_id'],
                       headers={'If-Match': signup['_etag']},
                       data={'user': str(user2['_id'])},
                       token=root_token,
                       status_code=422)

        # Check that email can not be patched
        self.api.patch('/eventsignups/%s' % signup['_id'],
                       headers={'If-Match': signup['_etag']},
                       data={'email': 'a@b.c'},
                       token=root_token,
                       status_code=422)

        # Check that event can not be patched
        self.api.patch('/eventsignups/%s' % signup['_id'],
                       headers={'If-Match': signup['_etag']},
                       data={'event': str(event2['_id'])},
                       token=root_token,
                       status_code=422)

        # Check that only admins can patch accepted
        self.api.patch('/eventsignups/%s' % signup['_id'],
                       headers={'If-Match': signup['_etag']},
                       data={'accepted': True},
                       token=user_token,
                       status_code=422)

        self.api.patch('/eventsignups/%s' % signup['_id'],
                       headers={'If-Match': signup['_etag']},
                       data={'accepted': True},
                       token=root_token,
                       status_code=200)

    def test_registration_window(self):
        """Test that signups out of the registration window are rejected for
        unpriviledged users."""
        t_open = datetime(2016, 1, 1)
        t_close = datetime(2016, 12, 31)

        ev = self.new_object("events", spots=100,
                             time_register_start=t_open,
                             time_register_end=t_close)
        user = self.new_object("users")
        token = self.get_user_token(user['_id'])
        root_token = self.get_root_token()

        # Too early
        with freeze_time(datetime(2015, 1, 1)):
            self.api.post("/eventsignups", data={
                'event': str(ev['_id']),
                'user': str(user['_id'])
            }, token=token, status_code=422)

        # Too late
        with freeze_time(datetime(2017, 1, 1)):
            self.api.post("/eventsignups", data={
                'event': str(ev['_id']),
                'user': str(user['_id'])
            }, token=token, status_code=422)

        # Correct time
        with freeze_time(datetime(2016, 6, 1)):
            self.api.post("/eventsignups", data={
                'event': str(ev['_id']),
                'user': str(user['_id'])
            }, token=token, status_code=201)

        user2 = self.new_object('users')

        # Admin can ignore time
        with freeze_time(datetime(2015, 1, 1)):
            self.api.post("/eventsignups", data={
                'event': str(ev['_id']),
                'user': str(user2['_id'])
            }, token=root_token, status_code=201)
