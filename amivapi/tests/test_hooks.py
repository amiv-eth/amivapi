import datetime as dt

from amivapi import models
from amivapi.tests import util

from amivapi.settings import DATE_FORMAT

import json


class HookTest(util.WebTestNoAuth):

    def test_a_Permission_hooks(self):
        # make new user
        user = self.new_user()
        userid = user.id

        # make new permission assignment with wrong expiry
        expiry = dt.datetime(2000, 11, 11)
        self.api.post("/permissions", data={
            'user_id': userid,
            'role': 'vorstand',
            'expiry_date': expiry.strftime(DATE_FORMAT),
        }, status_code=422)
        assignmentCount = self.db.query(models.Permission).count()
        self.assertEquals(assignmentCount, 0)

        # make new permission assignment with right data
        expiry = dt.datetime(2123, 11, 11)
        self.api.post("/permissions", data={
            'user_id': userid,
            'role': 'vorstand',
            'expiry_date': expiry.strftime(DATE_FORMAT),
        }, status_code=201)

        # has assignment got into the db?
        assignmentCount = self.db.query(models.Permission).count()
        self.assertEquals(assignmentCount, 1)

        # can we see the assignment from outside?
        permissions = self.api.get("/permissions", status_code=200)
        self.assertEquals(len(permissions.json['_items']), 1)
        self.assertEquals(permissions.json['_items'][0]['user_id'], userid)
        self.assertEquals(permissions.json['_items'][0]['role'], 'vorstand')

    def test_a_Permission_invalid_role(self):
        user = self.new_user()
        userid = user.id

        data = {
            'user_id': userid,
            'role': 'notafukinrole',
            'expiry_date': dt.datetime(3000, 1, 1).strftime(DATE_FORMAT)
        }
        self.api.post("/permissions", data=data, status_code=422)

        data['role'] = 'vorstand'
        self.api.post("/permissions", data=data, status_code=201)

    def test_b_EventSignup_hooks(self):
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
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
        }, status_code=422)
        signupCount = self.db.query(models._EventSignup).count()
        self.assertEquals(signupCount, 0)

        # sign up user 1 to wrong event
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid + 10,
            'user_id': userid,
        }, status_code=422)
        signupCount = self.db.query(models._EventSignup).count()
        self.assertEquals(signupCount, 0)

        # sign up user 1 with wrong departement
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'extra_data': {'department': 'infk'},
        }, status_code=422)
        signupCount = self.db.query(models._EventSignup).count()
        self.assertEquals(signupCount, 0)

        # sign up user 1 and do everything right
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': userid,
            'extra_data': {
                'department': 'itet',
            }
        }, status_code=201)
        signup1 = signup.json['id']

        signupCount = self.db.query(models._EventSignup).count()
        self.assertEquals(signupCount, 1)

        signups = self.api.get("/eventsignups", status_code=200)
        self.assertEquals(signups.json['_items'][signup1 - 1]['event_id'],
                          eventid)
        self.assertEquals(
            signups.json['_items'][signup1 - 1]['email'],
            "testuser-1@example.net"
        )

        # sign up hermanthegerman@amiv.ethz.ch
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': -1,
            'email': "hermanthegerman@amiv.ethz.ch",
            'extra_data': {'department': 'itet'},
        }, status_code=202)

        signupCount = self.db.query(models._EventSignup).count()
        self.assertEquals(signupCount, 1)

    """def test_Studydocuments(self):
        #make new files
        file1 = self.api.post("/files", data={
        })
    """
