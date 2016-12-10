# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test event validators."""

from pytz import utc
import json
from datetime import datetime, timedelta

from amivapi.tests.utils import WebTestNoAuth


class EventValidatorTest(WebTestNoAuth):
    """Test Class for event validation."""

    def event_data(self, data):
        """Add minimum needed data for an event (descriptions)."""
        return dict(title_en='party',
                    description_en='fun',
                    catchphrase_en='disco, disco, party, party',
                    **data)

    def test_signup_to_event_without_signup(self):
        """Test that signups to events without a signup are rejected."""
        ev = self.new_object("events", spots=None)
        user = self.new_object("users")

        self.api.post("/eventsignups", data={
            'event': str(ev['_id']),
            'user': str(user['_id'])
        }, status_code=422)

    def test_signup_out_of_registration_window(self):
        """Test that signups out of the registration window are rejected."""
        t_open = datetime.now(utc) - timedelta(days=2)
        t_close = datetime.now(utc) - timedelta(days=1)

        ev = self.new_object("events", spots=100,
                             time_register_start=t_open,
                             time_register_end=t_close)
        user = self.new_object("users")

        self.api.post("/eventsignups", data={
            'event': str(ev['_id']),
            'user': str(user['_id'])
        }, status_code=422)

    def test_additional_fields_must_match(self):
        """Test the validation of additional fields."""
        ev = self.new_object("events", spots=100,
                             additional_fields=json.dumps({
                                 'field1': {
                                     'type': 'string',
                                     'maxlength': 10
                                 },
                                 'field2': {
                                     'type': 'integer'
                                 }
                             }))

        user = self.new_object("users")

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

    def test_de_or_en_required(self):
        """Test that events need at least one language.

        This tests the depends_any validator.
        """
        self.api.post("/events", data={}, status_code=422)

        self.api.post("/events", data={
            'title_en': 'party',
            'description_en': 'fun',
            'catchphrase_en': 'disco, disco, party, party',
        }, status_code=201)

        self.api.post("/events", data={
            'title_de': 'party',
            'description_de': 'fun',
            'catchphrase_de': 'disco, disco, party, party',
        }, status_code=201)

    def test_later_than(self):
        """Test the later_than validator.

        We do this using the start and end date of an event.
        """
        self.api.post("/events", data=self.event_data({
            'time_start': '2016-10-17T21:11:14Z',
            'time_end': '2016-03-19T13:33:37Z'
        }), status_code=422)

        self.api.post("/events", data=self.event_data({
            'time_start': '2016-10-17T21:11:14Z',
            'time_end': '2017-03-19T13:33:37Z'
        }), status_code=201)

    def test_patch_later_than(self):
        """Test patching time dependent fields."""
        ev = self.new_object("events",
                             spots=1337,
                             time_start='2016-10-10T13:33:37Z',
                             time_end='2016-10-20T13:33:37Z')

        headers = {'If-Match': ev['_etag']}
        url = "/events/%s" % ev['_id']

        bad_start = {'time_start': '2016-10-25T13:33:37Z'}
        good_start = {'time_start': '2016-10-15T13:33:37Z'}

        bad_end = {'time_end': '2016-10-5T13:33:37Z'}
        good_end = {'time_end': '2016-10-26T13:33:37Z'}

        for bad in bad_start, bad_end:
            self.api.patch(url, headers=headers, data=bad, status_code=422)

        for good in good_start, good_end:
            r = self.api.patch(url, headers=headers,
                               data=good, status_code=200).json
            # Update etag for next request
            headers['If-Match'] = r['_etag']

    def test_spot_dependencies(self):
        """Test that the requires if not null validator works.

        We do this by trying to add an event with spots >= 0, but no
        further required data.
        """
        self.api.post('/events', data=self.event_data({
            'spots': 100
        }), status_code=422)

        self.api.post('/events', data=self.event_data({
            'spots': 100,
            'time_register_end': '2016-10-17T21:11:15Z',
            'allow_email_signup': True
        }), status_code=422)

        self.api.post('/events', data=self.event_data({
            'spots': 100,
            'time_register_start': '2016-10-17T21:11:14Z',
            'allow_email_signup': True
        }), status_code=422)

        self.api.post('/events', data=self.event_data({
            'spots': 100,
            'time_register_start': '2016-10-17T21:11:14Z',
            'time_register_end': '2016-10-17T21:11:15Z',
            'allow_email_signup': True
        }), status_code=201)

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

    def test_can_add_time_start(self):
        """ Test issue #141
        The validator of time_start (later_than) assumed, that the field is
        already existing on PATCH requests. Check that this is fixed.
        """
        ev = self.new_object("events", spots=100, allow_email_signup=False)

        data = {
            'time_start': "2016-01-01T00:00:00Z",
            'time_end': "2016-02-02T00:00:00Z"
        }
        ev = self.api.patch('/events/%s' % ev['_id'], data=data,
                            headers={'If-Match': ev['_etag']},
                            status_code=200).json
