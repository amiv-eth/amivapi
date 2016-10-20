# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test email confirmation system for external event signups"""

import re

from amivapi.tests.utils import WebTestNoAuth


class EventMailTest(WebTestNoAuth):
    def test_email_tokens(self):
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
        self.api.get('/confirm_email/%s' % token, status_code=302)

        # Check that the signup got confirmed
        signup = self.api.get('/eventsignups/%s' % signup['_id'],
                              status_code=200).json
        self.assertEqual(signup['confirmed'], True)
