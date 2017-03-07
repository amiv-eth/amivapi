# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test event model specific validators."""

import json

from amivapi.tests.utils import WebTestNoAuth


class EventModelTest(WebTestNoAuth):
    """Test class for event model specific validators."""

    def event_data(self, data):
        """Add minimum needed data for an event (descriptions)."""
        return dict(title_en='party',
                    description_en='fun',
                    catchphrase_en='disco, disco, party, party',
                    time_advertising_start='1970-01-01T00:00:01Z',
                    time_advertising_end='2020-01-01T00:00:00Z',
                    priority=5,
                    **data)

    def test_signup_to_event_without_signup(self):
        """Test that signups to events without a signup are rejected."""
        ev = self.new_object("events", spots=None)
        user = self.new_object("users")

        self.api.post("/eventsignups", data={
            'event': str(ev['_id']),
            'user': str(user['_id'])
        }, status_code=422)

    def test_additional_fields_must_match(self):
        """Test the validation of additional fields."""
        ev = self.new_object("events", spots=100,
                             additional_fields=json.dumps({
                                 'properties': {
                                     'field1': {
                                         'type': 'string',
                                         'maxLength': 10
                                     },
                                     'field2': {
                                         'type': 'integer'
                                     }},
                                 'required': ['field1']
                             }))

        user = self.new_object("users")

        self.api.post("/eventsignups", data={
            'user': str(user['_id']),
            'event': str(ev['_id']),
            'additional_fields': "{not even json}"
        }, status_code=422)

        self.api.post("/eventsignups", data={
            'user': str(user['_id']),
            'event': str(ev['_id']),
            'additional_fields': json.dumps({
                'field1': 'aaaaaaaaaaaaaaaaaaaaa',
                'field2': 0
            })
        }, status_code=422)

        self.api.post("/eventsignups", data={
            'user': str(user['_id']),
            'event': str(ev['_id']),
            'additional_fields': json.dumps({
                'field2': 0
            })
        }, status_code=422)

        self.api.post("/eventsignups", data={
            'user': str(user['_id']),
            'event': str(ev['_id']),
            'additional_fields': json.dumps({
                'field1': 'asdasdasd',
                'field2': 50
            })
        }, status_code=201)

    def test_email_signup_only_when_allowed(self):
        """Test that email signup is only possible if enabled."""
        ev = self.new_object("events", spots=100, allow_email_signup=False)
        self.api.post("/eventsignups", data={
            'email': 'bla@bla.org',
            'event': str(ev['_id'])
        }, status_code=422)

        ev = self.new_object("events", spots=100, allow_email_signup=True)
        self.api.post("/eventsignups", data={
            'email': 'bla@bla.org',
            'event': str(ev['_id'])
        }, status_code=201)

    def test_spots_none(self):
        """Test you can set spots to None and this does not require deps."""
        self.api.post('/events', data=self.event_data({
            'spots': None,
        }), status_code=201)

    def test_fields_depending_on_signup_not_null(self):
        """Test that signup needs to be not None for fields depending on it."""
        test_data = [
            {'allow_email_signup': True},
            {'additional_fields': ''},
            {'time_register_start': '2016-10-17T21:11:14Z'},
        ]
        # No need to test time end, this depends on time start anyway.

        for data in test_data:
            data = self.event_data(data)

            data['spots'] = None
            self.api.post('/events', data=data, status_code=422)

    def test_eventsignup_validators_work_without_event(self):
        """Test that none of the validators of eventsignups crash without an
        event"""
        user = self.new_object('users')

        self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'additional_fields': "{}"
        }, status_code=422)

        self.api.post('/eventsignups', data={
            'event': 'invalid',
            'user': str(user['_id']),
            'additional_fields': "{}"
        }, status_code=422)
