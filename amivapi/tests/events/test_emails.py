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

    def test_confirmation_email_when_user_null(self):
        """Test confirmation email when user is explicitly set to None."""
        event = self.new_object('events', spots=100, allow_email_signup=True)
        signup = self.api.post('/eventsignups', data={
            'event': str(event['_id']),
            'user': None,
            'email': 'bla@test.bla'
        }, status_code=201).json

        self.assertEqual(signup['confirmed'], False)
        self.assertEqual(len(self.app.test_mails), 1)

        # Look for sent out mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'][0], 'bla@test.bla')

    def test_email_signup_delete(self):
        """Test deletion of signup via email link."""
        event = self.new_object('events', spots=100, selection_strategy='fcfs')
        user = self.new_object('users')

        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]
        token = re.search(r'/delete_signup/(.+)\n', mail['text']).group(1)

        # With redirect set
        self.app.config['SIGNUP_DELETED_REDIRECT'] = "somewhere"
        self.api.get('/delete_signup/%s' % token, status_code=302)

        # Check that signup was deleted
        self.api.get('/eventsignups/%s' % signup['_id'], status_code=404)

        self.assertEqual(len(self.app.test_mails), 2)
        self.assertTrue(
            'successfully deregistered' in self.app.test_mails[1]['text'])

        # Another signup
        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[2]
        token = re.search(r'/delete_signup/(.+)\n', mail['text']).group(1)

        # Without redirect set
        self.app.config.pop('SIGNUP_DELETED_REDIRECT')
        self.api.get('/delete_signup/%s' % token, status_code=200)

        # Check that signup was deleted
        self.api.get('/eventsignups/%s' % signup['_id'], status_code=404)

    def test_email_direct_signup_by_moderator(self):
        """Test email on direct signup by a moderator"""
        user_id = 24 * '1'
        moderator_id = 24 * '2'
        event_id = 24 * '3'
        self.load_fixture({
            'users': [{
                '_id': user_id
            }, {
                '_id': moderator_id
            }],
            'events': [{
                '_id': event_id,
                'moderator': moderator_id,
                'spots': 100,
                'selection_strategy': 'manual'
            }],
        })

        self.api.post('/eventsignups',
                      data={
                          'user': user_id,
                          'event': event_id,
                          'accepted': True},
                      token=self.get_user_token(moderator_id),
                      status_code=201)

        self.assertEqual(len(self.app.test_mails), 1)
        print(self.app.test_mails[0]['text'])
        self.assertTrue('was accepted' in self.app.test_mails[0]['text'])

    def test_email_waiting_list(self):
        """Test all emails in the following process:
        1. User signs up for an event
        2. Event is full
        3. User is added to the waiting list
        4. First user deletes his signup, second user is accepted
        """
        user_id1 = 24 * '1'
        user_id2 = 24 * '2'
        event_id = 24 * '3'
        self.load_fixture({
            'users': [{
                '_id': user_id1
            }, {
                '_id': user_id2
            }],
            'events': [{
                '_id': event_id,
                'spots': 1,
                'selection_strategy': 'fcfs'
            }],
        })

        signup1 = self.api.post('/eventsignups', data={
            'event': event_id,
            'user': user_id1,
        }, status_code=201).json

        self.assertEqual(len(self.app.test_mails), 1)
        self.assertTrue('was accepted' in self.app.test_mails[0]['text'])

        _ = self.api.post('/eventsignups', data={
            'event': event_id,
            'user': user_id2,
        }, status_code=201).json

        self.assertEqual(len(self.app.test_mails), 2)
        self.assertTrue('was rejected' in self.app.test_mails[1]['text'])

        etag = {'If-Match': signup1['_etag']}
        self.api.delete("/eventsignups/" + str(signup1['_id']),
                        headers=etag, status_code=204)

        self.assertEqual(len(self.app.test_mails), 4)
        self.assertTrue(
            'successfully deregistered' in self.app.test_mails[2]['text'])
        self.assertTrue('was accepted' in self.app.test_mails[3]['text'])

    def test_invalid_token(self):
        """Test that an error is returned for an invalid token to the email
        link endpoints."""
        resp = self.api.get("/confirm_email/invalid", status_code=200).data
        self.assertEqual(resp, b'Unknown token')

        resp = self.api.get("/delete_signup/invalid", status_code=200).data
        self.assertEqual(resp, b'Unknown token')

    def test_external_signups_wait_for_confirmation(self):
        """Test that external signups do not get accepted until confirmed."""
        event = self.new_object('events', spots=100, selection_strategy='fcfs',
                                allow_email_signup=True)

        signup = self.api.post('/eventsignups', data={
            'email': 'a@example.com',
            'event': str(event['_id'])
        }, status_code=201).json

        # Signup should not be accepted yet
        self.assertTrue(not self.api.get('/eventsignups/%s' % signup['_id'],
                                         status_code=200).json['accepted'])

        mail = self.app.test_mails[0]
        token = re.search(r'/confirm_email/(.+)\n\n', mail['text']).group(1)

        self.api.get('/confirm_email/%s' % token, status_code=200)

        # Signup should now be accepted
        self.assertTrue(self.api.get('/eventsignups/%s' % signup['_id'],
                                     status_code=200).json['accepted'])

    def test_no_nones_in_emails(self):
        """Test that there are no 'None' values in any emails."""
        event = self.new_object('events', spots=100, selection_strategy='fcfs',
                                allow_email_signup=True)

        self.api.post('/eventsignups', data={
            'email': 'a@example.com',
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]

        for field in mail.values():
            self.assertTrue('None' not in field)

        token = re.search(r'/confirm_email/(.+)\n\n', mail['text']).group(1)
        self.api.get('/confirm_email/%s' % token, status_code=200)

        mail = self.app.test_mails[1]
        for field in mail.values():
            self.assertTrue('None' not in field)

    def test_reply_to_emails(self):
        # Check there is no `reply-to` header in email if no moderator is set.
        event = self.new_object('events', spots=100, selection_strategy='fcfs')
        user = self.new_object('users')

        self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]

        self.assertTrue('reply-to' not in mail)

        # Check whether `reply-to` header present in email if moderator is set.
        user_moderator = self.new_object('users', email='xyz@gmail.com')
        event2 = self.new_object('events', spots=100, 
                                 selection_strategy='fcfs', 
                                 moderator=user_moderator['_id'])

        self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event2['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[1]
        self.assertTrue(mail['reply-to'] == 'xyz@gmail.com')
