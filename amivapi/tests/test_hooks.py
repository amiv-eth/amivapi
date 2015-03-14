from amivapi import models
from amivapi.tests import util

import datetime as dt
import json


class HookTest(util.WebTestNoAuth):

    def test_b_eventsignup_hooks(self):
        # make new event
        event = self.new_event(additional_fields=json.dumps({
            'department': {
                'type': 'string',
                'required': True,
                'allowed': ['itet', 'mavt'],
            }}),
            time_register_start=dt.datetime.utcnow(),
            time_register_end=dt.datetime.today() + dt.timedelta(days=2),
            is_public=True,
        )
        eventid = event.id
        # make new user
        user = self.new_user(email=u"testuser-1@example.net")
        userid = user.id

        # Sign up user 1 without departement
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
        }, status_code=422)
        signup_count = self.db.query(models.EventSignup).count()
        self.assertEquals(signup_count, 0)

        # sign up user 1 to wrong event
        self.api.post("/eventsignups", data={
            'event_id': eventid + 10,
            'user_id': userid,
        }, status_code=422)
        signup_count = self.db.query(models.EventSignup).count()
        self.assertEquals(signup_count, 0)

        # sign up user 1 with wrong departement
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'extra_data': {'department': 'infk'},
        }, status_code=422)
        signup_count = self.db.query(models.EventSignup).count()
        self.assertEquals(signup_count, 0)

        # sign up user 1 and do everything right
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'extra_data': {
                'department': 'itet',
            }
        }, status_code=201)

        signup_count = self.db.query(models.EventSignup).count()
        self.assertEquals(signup_count, 1)

        signups = self.api.get("/eventsignups", status_code=200)
        self.assertEquals(signups.json['_items'][0]['event_id'],
                          eventid)
        self.assertEquals(
            signups.json['_items'][0]['email'],
            "testuser-1@example.net"
        )

        # sign up hermanthegerman@amiv.ethz.ch
        self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': -1,
            'email': "hermanthegerman@amiv.ethz.ch",
            'extra_data': {'department': 'itet'},
        }, status_code=202)

        signup_count = self.db.query(models.EventSignup).count()
        self.assertEquals(signup_count, 1)

    # def test_Studydocuments(self):
    #     #make new files
    #     file1 = self.api.post("/files", data={
    #     })
