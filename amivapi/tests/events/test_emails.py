# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test email confirmation system for external event signups."""

import datetime
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

    def test_calendar_invite_format(self):
        """Test that the calendar invite format.
        Specifically looks for the correct line format and the presence of
        required and desired fields.
        """
        event = self.new_object(
            'events',
            spots=100,
            selection_strategy='fcfs',
            allow_email_signup=True,
            time_start=datetime.datetime.strptime('2019-01-01T00:00:00Z',
                                                  '%Y-%m-%dT%H:%M:%SZ'),
            time_end=datetime.datetime.strptime('2019-01-01T01:00:00Z',
                                                '%Y-%m-%dT%H:%M:%SZ'),
            description_en=('Description\nSpanning\nmultiple\nlines.'),
        )

        user = self.new_object('users')

        self.api.post('/eventsignups',
                      data={
                          'user': str(user['_id']),
                          'event': str(event['_id'])
                      },
                      status_code=201).json

        mail = self.app.test_mails[0]

        # No missing fields of importance
        self.assertTrue(mail["calendar_invite"] is not None and
                        'None' not in mail["calendar_invite"])

        # Check the overall format
        non_null_fields = []
        for line in mail["calendar_invite"].splitlines():
            # Check that the line is not empty
            self.assertTrue(line)
            # Check the line format
            regex = r'^(?P<key>[A-Z\-]+)(?::|;(?P<params>.+?):)(?P<value>.*)$'
            re_match = re.match(regex, line)
            self.assertTrue(re_match)  # No empty or non-conforming lines
            if len(re_match.group("value")) > 0:
                non_null_fields.append(re_match.group("key"))
        # Check that the required and desired fields are present
        self.assertTrue('VERSION' in non_null_fields)
        self.assertTrue('PRODID' in non_null_fields)
        self.assertTrue('UID' in non_null_fields)
        self.assertTrue('DTSTAMP' in non_null_fields)
        self.assertTrue('DTSTART' in non_null_fields)
        self.assertTrue('DTEND' in non_null_fields)  # Not strictly required
        self.assertTrue('SUMMARY' in non_null_fields)  # Not strictly required

    def test_no_calendar_if_time_not_set(self):
        """Test that no calendar invite is created if the event has no time."""
        event = self.new_object(
            'events',
            spots=100,
            selection_strategy='fcfs',
            allow_email_signup=True,
            time_start=None,
            time_end=None,
        )

        user = self.new_object('users')

        self.api.post('/eventsignups',
                      data={
                          'user': str(user['_id']),
                          'event': str(event['_id'])
                      },
                      status_code=201)

        mail = self.app.test_mails[0]

        self.assertTrue(mail.get("calendar_invite") is None)

    def test_moderator_reply_to(self):
        """Check whether `reply-to` header is the moderator in email if set."""
        user = self.new_object('users')
        user_moderator = self.new_object('users', email='xyz@gmail.com')
        event = self.new_object('events', spots=100,
                                selection_strategy='fcfs',
                                moderator=user_moderator['_id'])

        self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]
        self.assertTrue(mail['reply-to'] == 'xyz@gmail.com')

    def test_all_emails_for_reply_to_header(self):
        """Check that the `reply-to` header in all email is set to default"""
        reply_to_email = self.app.config.get('DEFAULT_EVENT_REPLY_TO')
        event1 = self.new_object('events', spots=100,
                                 selection_strategy='manual')
        event2 = self.new_object('events', spots=100,
                                 selection_strategy='fcfs',
                                 allow_email_signup=True)
        user = self.new_object('users')

        # signup of external user
        _ = self.api.post('/eventsignups', data={
            'email': 'a@example.com',
            'event': str(event2['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]
        token = re.search(r'/confirm_email/(.+)\n\n', mail['text']).group(1)

        self.api.get('/confirm_email/%s' % token, status_code=200)

        # signup to waitlist
        signup1 = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event1['_id'])
        }, status_code=201).json

        # delete signup
        etag = {'If-Match': signup1['_etag']}
        self.api.delete("/eventsignups/" + str(signup1['_id']),
                        headers=etag, status_code=204)

        for i in range(len(self.app.test_mails)):
            mail = self.app.test_mails[i]
            self.assertTrue(mail['reply-to'] == reply_to_email)

    def test_signup_additional_info(self):
        text = "We will meet at 9:30."
        event = self.new_object('events', spots=100, selection_strategy='fcfs',
                                title_en='title',
                                description_en='Description',
                                catchphrase_en='catchphrase',
                                signup_additional_info_en=text)
        user = self.new_object('users')

        self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        mail = self.app.test_mails[0]
        self.assertTrue(text in mail['text'])

    def test_notify_waitlist_on_signup_update(self):
        """Test that users on the waiting list get notified when a moderator
        updates his signup acceptance."""
        # Case 1: Manual Event with waiting list
        manual_event = self.new_object('events',
                                       spots=100,
                                       selection_strategy='manual',
                                       allow_email_signup=True)
        manual_user = self.new_object('users')

        # User put on waiting list
        manual_signup = self.api.post('/eventsignups',
                                      data={
                                          'user': str(manual_user['_id']),
                                          'event': str(manual_event['_id'])
                                      },
                                      status_code=201).json
        self.assertTrue('was rejected' in self.app.test_mails[0]['text'])

        # User manually accepted from waiting list
        self.api.patch('/eventsignups/%s' % manual_signup['_id'],
                       data={'accepted': True},
                       status_code=200,
                       headers={'If-Match': manual_signup['_etag']})
        self.assertTrue('was accepted' in self.app.test_mails[1]['text'])

        # Case 2: Full FCFS event with waiting list: User deregistered after
        # deregistration deadline by contacting moderators and they
        # manually accept a new user
        fcfc_user_accepted = self.new_object('users')
        fcfc_user_waitlist = self.new_object('users')
        fcfc_event = self.new_object('events',
                                     spots=1,
                                     selection_strategy='fcfs',
                                     allow_email_signup=True)
        # User accepted
        self.api.post('/eventsignups',
                      data={
                          'user': str(fcfc_user_accepted['_id']),
                          'event': str(fcfc_event['_id'])
                      },
                      status_code=201)
        self.assertTrue('was accepted' in self.app.test_mails[2]['text'])

        # User put on waiting list
        fcfc_signup_waitlist = self.api.post(
            '/eventsignups',
            data={
                'user': str(fcfc_user_waitlist['_id']),
                'event': str(fcfc_event['_id'])
            },
            status_code=201).json
        print(self.app.test_mails[2]['text'])
        self.assertTrue('was rejected' in self.app.test_mails[3]['text'])

        # User manually accepted from waiting list
        self.api.patch('/eventsignups/%s' % fcfc_signup_waitlist['_id'],
                       data={'accepted': True},
                       headers={'If-Match': fcfc_signup_waitlist['_etag']},
                       status_code=200)
        self.assertTrue('was accepted' in self.app.test_mails[4]['text'])
