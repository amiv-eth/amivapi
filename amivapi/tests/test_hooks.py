import datetime as dt

from amivapi import models
from amivapi.tests import util

from amivapi.settings import DATE_FORMAT


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
            'expiry_date': expiry.isoformat(),
        }, status_code=422)
        assignmentCount = self.db.query(models.Permission).count()
        self.assertEquals(assignmentCount, 0)

        # make new permission assignment with right data
        expiry = dt.datetime(2123, 11, 11)
        self.api.post("/permissions", data={
            'user_id': userid,
            'role': 'vorstand',
            'expiry_date': expiry.isoformat(),
        }, status_code=201)

        # has assignment got into the db?
        assignmentCount = self.db.query(models.Permission).count()
        self.assertEquals(assignmentCount, 1)

        # can we see the assignment from outside?
        permissions = self.api.get("/permissions", status_code=200)
        self.assertEquals(len(permissions.json['_items']), 1)
        self.assertEquals(permissions.json['_items'][0]['user_id'], userid)
        self.assertEquals(permissions.json['_items'][0]['role'], 'vorstand')

    def test_b_EventSignup_hooks(self):
        # make new event
        start = dt.datetime.today() + dt.timedelta(days=2)
        event = self.api.post("/events", data={
            'title': "Awesome Test Event",
            'time_start': start.strftime(DATE_FORMAT),
            'is_public': True,
            'price': '0',
            'spots': 10,
            'time_register_start': dt.datetime.now().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': (
                "{{"
                "'name':'departement',"
                "'type':'radiobutton',"
                "'button1':'ITET',"
                "'button2':'MAVT'"
                "}}"
            )
        }, status_code=201)
        eventid = event.json['id']

        # Sign up user 1 without departement
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': 1,
        }, status_code=422)
        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 0)

        # sign up user 1 to wrong event
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid + 10,
            'user_id': 1,
        }, status_code=422)
        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 0)

        # sign up user 1 with wrong departement
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': 1,
            'additional_data': "{'departement': 'INFK'}"
        }, status_code=422)
        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 0)

        # sign up user 1 and do everything right
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': 1,
            'additional_data': "{'departement': 'ITET'}",
        }, status_code=201)
        signup1 = signup.json['id']

        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 1)

        signups = self.api.get("/eventsignups", status_code=200)
        self.assertEquals(signups.json['_items'][signup1]['event_id'], eventid)
        self.assertEquals(
            signups.json['_items'][signup1]['email'],
            "max-muster@example.net"
        )

        # sign up hermanthegerman@amiv.ethz.ch
        signup = self.api.post("/eventsignups", data={
            'event_id': eventid,
            'user_id': -1,
            'email': "hermanthegerman@amiv.ethz.ch",
            'additional_data': "{'department': 'ITET'}",
        }, status_code=201)

        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 2)

    """def test_Studydocuments(self):
        #make new files
        file1 = self.api.post("/files", data={
        })
    """
