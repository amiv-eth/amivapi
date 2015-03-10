from amivapi.tests import util

import json


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

        event = self.new_event(is_public=True, spots=10,
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
            'extra_data': {'department': 'itet'}
        }

        # does not work without session
        self.api.post("/eventsignups", data=data, status_code=401)

        ticket = self.api.post("/eventsignups", token=user_token, data=data,
                               status_code=201).json

        # Try to PATCH the eventsignup-extradata
        ticket = self.api.patch("/eventsignups/%d" % ticket['_id'],
                                data={'extra_data': {'department': 'mavt'}},
                                headers={'If-Match': ticket['_etag']},
                                token=user_token,
                                status_code=201).json

        # DELETE the signup as other user -> not allowed
        self.api.delete("/eventsignups/%i" % ticket['_id'],
                        token=peon_token, status_code=403,
                        headers={'If-Match': ticket['_etag']})

        # DELETE the signup
        self.api.delete("/eventsignups/%i" % ticket['_id'],
                        token=user_token, status_code=200,
                        headers={'If-Match': ticket['_etag']})

        # DELETE peon's signup as vorstand
        vorstand = self.new_user(role='vorstand')
        vorstand_token = self.new_session(user_id=vorstand.id).token

        self.api.delete("/eventsignups/%i" % other_signup.id,
                        token=vorstand_token, status_code=200,
                        headers={'If-Match': other_signup._etag})

    def test_non_public_eventsignup(self):
        """Test /eventsignups for registered user and private event"""
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_token = self.new_session(user_id=admin.id).token
        peon = self.new_user()
        peon_token = self.new_session(user_id=peon.id).token

        payload = json.dumps({'department': {
                              'type': 'string',
                              'required': True,
                              'allowed': ['itet', 'mavt'],
                              }})

        event = self.new_event(is_public=False, spots=10,
                               additional_fields=payload)
        event2 = self.new_event(is_public=False, spots=10,
                                additional_fields=payload)

        # let's signup our user
        data = {
            'event_id': event.id,
            'user_id': user.id,
            'extra_data': {'department': 'itet'}
        }

        # does not work without session
        self.api.post("/eventsignups", data=data, status_code=401)

        # does not work from another user
        self.api.post("/eventsignups", data=data, token=peon_token,
                      status_code=403)
        # does work with session
        self.api.post("/eventsignups", data=data, token=user_token,
                      status_code=201)

        # does work as admin
        data = {
            'event_id': event2.id,
            'user_id': user.id,
            'extra_data': {'department': 'itet'}
        }
        self.api.post("/eventsignups", data=data, token=admin_token,
                      status_code=201)

        # does also not work with email-address
        data = {
            'event_id': event.id,
            'user_id': -1,
            'email': 'hallo@amiv.ch',
            'extra_data': {'department': 'itet'}
        }
        self.api.post("/eventsignups", data=data, token=user_token,
                      status_code=403)
        # also not as admin
        self.api.post("/eventsignups", data=data, token=admin_token,
                      status_code=403)
