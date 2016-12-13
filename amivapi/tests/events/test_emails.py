# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test email confirmation system for external event signups."""

import re

from amivapi.tests.utils import WebTestNoAuth


class EventMailTest(WebTestNoAuth):
    """Test tokens."""

    def test_email_tokens(self):
        """Test confirmation by email link."""
        event = self.new_object('events', spots=100, allow_email_signup=True)
        signup = self.api.post('/eventsignups', data={
            'event': str(event['_id']),
            'email': 'bla@test.bla'
        }, status_code=201).json

        self.assertEqual(signup['confirmed'], False)
        self.assertEqual(len(self.app.test_mails), 1)

        # Look for sent out mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'][0], 'bla@test.bla')

        # Use the confirm link
        token = re.search(r'/confirm_email/(.+)\n\n', mail['text']).group(1)
        # With redirect set
        self.app.config['EMAIL_CONFIRMED_REDIRECT'] = "somewhere"
        self.api.get('/confirm_email/%s' % token, status_code=302)
        # And without
        self.app.config.pop('EMAIL_CONFIRMED_REDIRECT')
        self.api.get('/confirm_email/%s' % token, status_code=200)

        # Check that the signup got confirmed
        signup = self.api.get('/eventsignups/%s' % signup['_id'],
                              status_code=200).json
        self.assertEqual(signup['confirmed'], True)

    def test_email_signup_delete(self):
        """Test deletion of signup via email link."""
        event = self.new_object('events', spots=100, selection_strategy='fcfs')
        user = self.new_object('users')

        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]
        token = re.search(r'/delete_signup/(.+)\n\n', mail['text']).group(1)

        # With redirect set
        self.app.config['SIGNUP_DELETED_REDIRECT'] = "somewhere"
        self.api.get('/delete_signup/%s' % token, status_code=302)

        # Check that signup was deleted
        self.api.get('/eventsignups/%s' % signup['_id'], status_code=404)

        # Another signup
        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[1]
        token = re.search(r'/delete_signup/(.+)\n\n', mail['text']).group(1)

        # Without redirect set
        self.app.config.pop('SIGNUP_DELETED_REDIRECT')
        self.api.get('/delete_signup/%s' % token, status_code=200)

        # Check that signup was deleted
        self.api.get('/eventsignups/%s' % signup['_id'], status_code=404)
