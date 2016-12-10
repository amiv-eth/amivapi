# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from datetime import datetime, timedelta

from amivapi.tests import util

from amivapi.settings import DATE_FORMAT

import json


class EventAccessTest(util.WebTest):
    def test_event_access(self):
        """ Tests that all events are publicly available """
        n = 10

        for _ in range(n):
            self.new_event()

        events = self.api.get("/events").json

        self.assertTrue(len(events['_items']) == n)


class EventTest(util.WebTestNoAuth):
    """ This class contains test for events"""

    def test_additional_fields(self):
        """ Test correct validation of 'additional_fields'"""
        start = datetime.today() + timedelta(days=2)

        # Invalid JSON
        self.api.post("/events", data={
            'time_start': start.strftime(DATE_FORMAT),
            'allow_email_signup': True,
            'price': 0,
            'spots': 10,
            'time_register_start': datetime.utcnow().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': "{[{Nope, not today{"
        }, status_code=422)

        # Now JSON, but no JSON object
        self.api.post("/events", data={
            'time_start': start.strftime(DATE_FORMAT),
            'allow_email_signup': True,
            'price': 0,
            'spots': 10,
            'time_register_start': datetime.utcnow().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': json.dumps(['I', 'am', 'a', 'list'])
        }, status_code=422)

        # Now JSON Object, but not a correct schema
        self.api.post("/events", data={
            'time_start': start.strftime(DATE_FORMAT),
            'allow_email_signup': True,
            'price': 0,
            'spots': 10,
            'time_register_start': datetime.utcnow().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': json.dumps({
                'department': {
                    'type': 'lol'
                }
            })
        }, status_code=422)

        # Now everything correct
        self.api.post("/events", data={
            'time_start': start.strftime(DATE_FORMAT),
            'allow_email_signup': True,
            'price': 0,
            'spots': 10,
            'time_register_start': datetime.utcnow().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': json.dumps({
                'department': {
                    'type': 'string',
                }
            })
        }, status_code=201)

        # Double check that its nullable
        self.api.post("/events", data={
            'time_start': start.strftime(DATE_FORMAT),
            'allow_email_signup': True,
            'price': 0,
            'spots': 10,
            'time_register_start': datetime.utcnow().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT)
        }, status_code=201)

    def test_price(self):
        """Test price formatting, decimals and negativ numbers forbidden"""
        start = (datetime.today() + timedelta(days=21)).strftime(DATE_FORMAT)
        end = (datetime.today() + timedelta(days=42)).strftime(DATE_FORMAT)

        self.api.post("/events", data={
            'time_start': end,
            'allow_email_signup': True,
            'price': 0,
            'spots': 10,
            'time_register_start': start,
            'time_register_end': end
        }, status_code=201)

        self.api.post("/events", data={
            'time_start': end,
            'allow_email_signup': True,
            'price': 10.5,
            'spots': 10,
            'time_register_start': start,
            'time_register_end': end
        }, status_code=422)

        self.api.post("/events", data={
            'time_start': end,
            'allow_email_signup': True,
            'price': -10,
            'spots': 10,
            'time_register_start': start,
            'time_register_end': end
        }, status_code=422)

    def test_spots_and_time(self):
        """ This test will create an event with signup. This means registration
        times are required
        """
        time_1 = datetime.today().strftime(DATE_FORMAT)
        time_2 = (datetime.today() + timedelta(days=21)).strftime(DATE_FORMAT)
        time_3 = (datetime.today() + timedelta(days=42)).strftime(DATE_FORMAT)

        # Post without registration timee
        self.api.post("/events", data={
            'time_start': time_3,
            'allow_email_signup': True,
            'spots': 10,
        }, status_code=422)

        # Post only with one time

        self.api.post("/events", data={
            'time_start': time_3,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_1
        }, status_code=422)

        self.api.post("/events", data={
            'time_start': time_3,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_end': time_2
        }, status_code=422)

        # Post correctly
        self.api.post("/events", data={
            'time_start': time_3,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_1,
            'time_register_end': time_2
        }, status_code=201)

    def test_swapped_time(self):
        """ Tests that end times have to be later or equal start times
        """
        time_1 = datetime.today().strftime(DATE_FORMAT)
        time_2 = (datetime.today() + timedelta(days=21)).strftime(DATE_FORMAT)
        time_3 = (datetime.today() + timedelta(days=42)).strftime(DATE_FORMAT)
        time_4 = (datetime.today() + timedelta(days=63)).strftime(DATE_FORMAT)

        # End before start
        self.api.post("/events", data={
            'time_start': time_4,
            'time_end': time_3,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_2,
            'time_register_end': time_1
        }, status_code=422)

        self.api.post("/events", data={
            'time_start': time_3,
            'time_end': time_4,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_2,
            'time_register_end': time_1
        }, status_code=422)

        self.api.post("/events", data={
            'time_start': time_4,
            'time_end': time_3,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_1,
            'time_register_end': time_2
        }, status_code=422)

        # Now correct
        self.api.post("/events", data={
            'time_start': time_3,
            'time_end': time_4,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_1,
            'time_register_end': time_2
        }, status_code=201)

        # Test incomplete
        self.api.post("/events", data={
            'time_end': time_4,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_start': time_1,
            'time_register_end': time_2
        }, status_code=422)

        self.api.post("/events", data={
            'time_start': time_3,
            'allow_email_signup': True,
            'spots': 10,
            'time_register_end': time_2
        }, status_code=422)

    def test_signup_count(self):
        """ Test whether the signup_count property works """

        start = datetime.today() - timedelta(days=1)
        end = datetime.today() + timedelta(days=1)
        ev = self.new_event(time_register_start=start, time_register_end=end)

        event_resp = self.api.get("/events/%i" % ev.id, status_code=200).json
        self.assertEqual(event_resp['signup_count'], 0)

        self.new_signup(event_id=ev.id, user_id=0)

        event_resp = self.api.get("/events/%i" % ev.id, status_code=200).json
        self.assertEqual(event_resp['signup_count'], 1)

        user = self.new_user()
        self.new_signup(event_id=ev.id, user_id=user.id)
        event_resp = self.api.get("/events/%i" % ev.id, status_code=200).json
        self.assertEqual(event_resp['signup_count'], 2)


class SignupTest(util.WebTest):
    def test_get_eventsignups_user(self):
        """Test /eventsignups for registered user and public event"""
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token
        peon = self.new_user()
        peon_token = self.new_session(user_id=peon.id).token

        payload = json.dumps({'department': {
                              'type': 'string',
                              'required': True,
                              'allowed': ['itet', 'mavt'],
                              }})

        event = self.new_event(allow_email_signup=True, spots=10,
                               additional_fields=payload)

        other_signup = self.new_signup(user_id=peon.id, event_id=event.id)

        # user cannot see other eventsignups
        signups = self.api.get("/eventsignups", token=user_token,
                               status_code=200).json['_items']
        self.assertEquals(len(signups), 0)

        # peon can see his signup
        signups = self.api.get("/eventsignups", token=peon_token,
                               status_code=200).json['_items']
        self.assertEquals(len(signups), 1)

        # let's signup our user
        data = {
            'event_id': event.id,
            'user_id': user.id,
            'additional_fields': json.dumps({'department': 'itet'})
        }

        # does not work without session
        self.api.post("/eventsignups", data=data, status_code=401)

        ticket = self.api.post("/eventsignups", token=user_token, data=data,
                               status_code=201).json

        # Try to PATCH the eventsignup additional fields
        ticket = self.api.patch("/eventsignups/%d" % ticket['_id'],
                                data={'additional_fields':
                                      '{"department": "mavt"}'},
                                headers={'If-Match': ticket['_etag']},
                                token=user_token,
                                status_code=200).json

        # DELETE the signup as unpriviledged user -> resource not visible
        self.api.delete("/eventsignups/%i" % ticket['id'],
                        token=peon_token, status_code=404,
                        headers={'If-Match': ticket['_etag']})

        # DELETE the signup
        self.api.delete("/eventsignups/%i" % ticket['id'],
                        token=user_token, status_code=204,
                        headers={'If-Match': ticket['_etag']})

        # DELETE peon's signup as vorstand
        vorstand = self.new_user()
        group = self.new_group(permissions={'eventsignups': {'DELETE': 1}})
        self.new_group_member(group_id=group.id, user_id=vorstand.id)
        vorstand_token = self.new_session(user_id=vorstand.id).token

        self.api.delete("/eventsignups/%i" % other_signup.id,
                        token=vorstand_token, status_code=204,
                        headers={'If-Match': other_signup._etag})

    def test_non_public_event_signup(self):
        """Test /eventsignups for registered user and private event"""
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token

        admin = self.new_user()
        # Create a group with permissions and add admin
        g = self.new_group(permissions={
                           "eventsignups": {"POST": True}
                           })
        self.new_group_member(user_id=admin.id, group_id=g.id)

        admin_token = self.new_session(user_id=admin.id).token
        peon = self.new_user()
        peon_token = self.new_session(user_id=peon.id).token

        payload = json.dumps({'department': {
                              'type': 'string',
                              'required': True,
                              'allowed': ['itet', 'mavt'],
                              }})

        event = self.new_event(allow_email_signup=False, spots=10,
                               additional_fields=payload)
        event2 = self.new_event(allow_email_signup=False, spots=10,
                                additional_fields=payload)

        # let's signup our user
        data = {
            'event_id': event.id,
            'user_id': user.id,
            'additional_fields': json.dumps({'department': 'itet'})
        }

        # does not work without session
        self.api.post("/eventsignups", data=data, status_code=401)

        # does not work from another user
        self.api.post("/eventsignups", data=data, token=peon_token,
                      status_code=422)
        # does work with session
        self.api.post("/eventsignups", data=data, token=user_token,
                      status_code=201)

        # does work as admin
        data = {
            'event_id': event2.id,
            'user_id': user.id,
            'additional_fields': json.dumps({'department': 'itet'})
        }
        self.api.post("/eventsignups", data=data, token=admin_token,
                      status_code=201)

        # non-public event does not work with email-address and token
        data = {
            'event_id': event.id,
            'user_id': -1,
            'email': 'hallo@amiv.ch',
            'additional_fields': json.dumps({'department': 'itet'})
        }
        self.api.post("/eventsignups", data=data, token=user_token,
                      status_code=422)
        # also not as admin, here it reports that -1 is not valid for non-
        # public events
        self.api.post("/eventsignups", data=data, token=admin_token,
                      status_code=422)

        # Now try to post to an nonexistent event (public can not be
        # determined)
        data = {
            'event_id': event.id + 42,
            'user_id': -1,
            'email': 'hallo@amiv.ch',
            'additional_fields': json.dumps({'department': 'itet'})
        }
        self.api.post("/eventsignups", data=data, token=admin_token,
                      status_code=422)


class SignupDataTest(util.WebTestNoAuth):
    """Test additional properties of signups that does not require auth
    """
    def test_user_signup(self):
        """ Test basic syntax: user can signup with id and no mail,
        unregistered users only with mail and user set to -1 (anonymous)
        """
        # Create event and user
        eventid = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=True,
            spots=10
        ).id
        userid = self.new_user().id

        # Post signup for user correctly
        self.api.post("/eventsignups",
                      data={'event_id': eventid,
                            'user_id': userid},
                      status_code=201)

        # Try to post with user and email, should fail
        self.api.post("/eventsignups",
                      data={'event_id': eventid,
                            'user_id': userid,
                            'email': 'ceo@alexcorp.de'},
                      status_code=422)

    def test_mail_signup(self):
        """ This test will check signup per mail.
        user has to be -1 if posting a mail"""
        # Create event
        eventid = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=True,
        ).id

        # Post correctly with mail and user set to -1
        self.api.post("/eventsignups",
                      data={'event_id': eventid,
                            'user_id': -1,
                            'email': 'ceo@alexcorp.de'},
                      status_code=202).json

        # Post incorrectly without user id
        self.api.post("/eventsignups",
                      data={'event_id': eventid,
                            'email': 'ceo@alexcorp.de'},
                      status_code=422)

        # Post incorrecly with id of a user and email
        userid = self.new_user().id
        self.api.post("/eventsignups",
                      data={'user_id': userid,
                            'event_id': eventid,
                            'email': 'ceo@alexcorp.de'},
                      status_code=422)

    def test_signups_with_additional_data(self):
        """ This test will test signing up for an event with "additional data"
        fields
        """
        # make a user that will sign up to event
        user = self.new_user()
        userid = user.id

        # Pre-test: Event without additional data
        event = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=False,
            spots=10
        )
        eventid = event.id

        # Try posting signup
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
        }, status_code=201)

        # make new event with additional fields
        event = self.new_event(additional_fields=json.dumps({
            'department': {
                'type': 'string',
                'required': True,
                'allowed': ['itet', 'mavt'],
            }}),
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=False,
        )
        eventid = event.id

        # Try posting empty string
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'additional_fields': ''
        }, status_code=422)

        # Try posting without data
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
        }, status_code=422)

        # Try posting with additional data that isnt json
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'additional_fields': 42,
        }, status_code=422)

        # Try posting with additional data that doesnt fit the schema
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'additional_fields': json.dumps({'department': 'infk'}),
        }, status_code=422)

        # Now post working data
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'additional_fields': json.dumps({'department': 'mavt'}),
        }, status_code=201)

        # Post working data to nonexistent event. Validator can not find schema
        # to validate additional fields now, but should not crash
        # (Response should contain issues but not a exception)
        r = self.api.post("/eventsignups", data={
            'event_id': 42,
            'user_id': userid,
            'additional_fields': json.dumps({'department': 'mavt'}),
        }, status_code=422).json
        self.assertFalse('exception' in r['_issues'].keys())

        # Now with missing event id
        r = self.api.post("/eventsignups", data={
            'user_id': userid,
            'additional_fields': json.dumps({'department': 'mavt'}),
        }, status_code=422).json
        self.assertFalse('exception' in r['_issues'].keys())

    def test_signup_twice(self):
        """Test to signup twice for same event"""
        event = self.new_event(additional_fields=json.dumps({
            'department': {
                'type': 'string',
                'required': True,
                'allowed': ['itet', 'mavt'],
            }}),
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=True,
        )
        eventid = event.id

        event_alt = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=True,
            spots=10
        )
        eventid_alt = event_alt.id

        user = self.new_user()
        userid = user.id

        # Try to sign up with user
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'additional_fields': json.dumps({'department': 'mavt'}),
        }, status_code=201)

        # Try to sign up again, should not work
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'additional_fields': json.dumps({'department': 'itet'}),
        }, status_code=422)

        # Try to sign up to different event, should be possible
        self.api.post("/eventsignups", data={
            'event_id': eventid_alt,
            'user_id': userid,
        }, status_code=201)

        # Try to sign up with mail
        self.api.post("/eventsignups", data={
            'user_id': -1,
            'event_id': eventid,
            'email': 'alex@alex.de',
            'additional_fields': json.dumps({'department': 'mavt'}),
        }, status_code=202)

        # Try to sign up again, should not work
        self.api.post("/eventsignups", data={
            'user_id': -1,
            'event_id': eventid,
            'email': 'alex@alex.de',
            'additional_fields': json.dumps({'department': 'itet'}),
        }, status_code=422)

        # Try to sign up to different event, should be possible
        self.api.post("/eventsignups", data={
            'user_id': -1,
            'event_id': eventid_alt,
            'email': 'alex@alex.de',
        }, status_code=202)

    def test_patch_signup(self):
        """Users should be able to alter the additional_fields but not ids.
        It is not intended to switch a user to a different one or move the
        (succesful) signup to a different event
        """
        # Create two events and users
        event_1 = self.new_event(additional_fields=json.dumps({
            'department': {
                'type': 'string',
                'required': True,
                'allowed': ['itet', 'mavt'],
            }}),
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=False,
        )
        eventid_1 = event_1.id
        event_2 = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=False,
        )
        eventid_2 = event_2.id

        userid_1 = self.new_user().id
        userid_2 = self.new_user().id

        # Post Signup
        r = self.api.post("/eventsignups", data={
            'event_id': eventid_1,
            'user_id': userid_1,
            'additional_fields': json.dumps({'department': 'mavt'}),
        }, status_code=201).json
        signupid = r['id']
        header = {'If-Match': r['_etag']}

        # Try changing user, should fail
        self.api.patch("/eventsignups/%i" % signupid, headers=header, data={
            'user_id': userid_2,
        }, status_code=422)

        # Try changing event, should fail
        self.api.patch("/eventsignups/%i" % signupid, headers=header, data={
            'event_id': eventid_2,
        }, status_code=422)

        # Try changing additional_data, should succeed
        self.api.patch("/eventsignups/%i" % signupid, headers=header, data={
            'additional_fields': json.dumps({'department': 'itet'})
        }, status_code=200)

    def test_not_sending_additional(self):
        """ This test will try not sending additional data even though the
        additional data field in event has required elements. Validation should
        not be skipped!"""

    def test_event_without_signup(self):
        """ This test will create an event with zero spots, signup shouldn't
        work - the eventid is not valid for a signup
        """
        eventid = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=False,
            spots=-1
        ).id

        userid = self.new_user().id

        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
        }, status_code=422)

    def test_signup_time(self):
        """ This test will create an event with signup window in the future
        and tries to sign up immediately, should fail

        Also tries to sign up after the signup period
        """
        future_event_id = self.new_event(
            time_register_start=datetime.today() + timedelta(days=21),
            time_register_end=datetime.today() + timedelta(days=42),
            allow_email_signup=False
        ).id

        past_event_id = self.new_event(
            time_register_start=datetime.today() - timedelta(days=42),
            time_register_end=datetime.today() - timedelta(days=21),
            allow_email_signup=False
        ).id

        userid = self.new_user().id

        self.api.post("/eventsignups", data={
            'event_id': future_event_id,
            'user_id': userid,
        }, status_code=422)

        self.api.post("/eventsignups", data={
            'event_id': past_event_id,
            'user_id': userid,
        }, status_code=422)

    def test_bulk_insert_and_get(self):
        return  # TODO
        """ Test if the custom hooks in confirm works as well when many items
        are requested, like bulk insert or get at resource level """
        eventid = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=True,
            spots=10
        ).id

        data = [{'user_id': -1,
                 'event_id': eventid,
                 'email': '1@test.de'},
                {'user_id': -1,
                 'event_id': eventid,
                 'email': '2@test.de'},
                {'user_id': -1,
                 'event_id': eventid,
                 'email': '3@test.de'},
                ]

        response = (self.api.post('/eventsignups', data=data, status_code=201)
                    .json)

        print(response)

        # Make sure the hook worked correctly for each item
        items = response['_items']
        self.assertTrue(items[0]['email'] == data[0]['email'])
        self.assertTrue(items[1]['email'] == data[1]['email'])
        self.assertTrue(items[2]['email'] == data[2]['email'])

        response = (self.api.get('/eventsignups', status_code=200)
                    .json)

        # Test again!
        items = response['_items']
        self.assertTrue(items[0]['email'] == data[0]['email'])
        self.assertTrue(items[1]['email'] == data[1]['email'])
        self.assertTrue(items[2]['email'] == data[2]['email'])

    def test_hidden_fields(self):
        """ The fields _email_unregistered and _token are for internal use only
        and should not be visible from outside """
        eventid = self.new_event(
            time_register_start=datetime.utcnow(),
            time_register_end=datetime.today() + timedelta(days=2),
            allow_email_signup=True,
            spots=10
        ).id

        signupid = self.api.post("eventsignups", data={
            'event_id': eventid,
            'user_id': -1,
            'email': 'ceo@alexcorp.com'
        }, status_code=202).json['id']

        response = (self.api.get("eventsignups/%s" % signupid, status_code=200)
                    .json)

        self.assertFalse('_email_unreg' in response.keys())
        self.assertFalse('_token' in response.keys())
