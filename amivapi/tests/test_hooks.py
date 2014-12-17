import datetime as dt

from amivapi import models
from amivapi.tests import util


class DataRelationshipTest(util.WebTest):

    def test_a_UserGroupRelations(self):
        # make new user
        user = self.api.post("/users", data={
            'firstname': "Max",
            'lastname': "Muster",
            'email': "max-muster@example.net",
            'gender': "male",
            'username': "maxm",
        }, status_code=201)
        userid = user.json['id']

        #make new group
        group = self.api.post("/groups", data={
            'name': "TestUsers",
        }, status_code=201)
        groupid = group.json['id']

        #make new Group-Assignment with wrong expiry
        expiry = dt.datetime(2000, 11, 11)
        membership = self.api.post("/groupmemberships", data={
            'user_id': userid,
            'group_id': groupid,
            'expiry_date': expiry.isoformat(),
        }, status_code=422)
        assignmentCount = self.db.query(models.GroupMembership).count()
        self.assertEquals(assignmentCount, 0)

        #make new Group-Assignment with right data
        expiry = dt.datetime(2123, 11, 11)
        membership = self.api.post("/groupmemberships", data={
            'user_id': userid,
            'group_id': groupid,
            'expiry_date': expiry.isoformat(),
        }, status_code=201)

        #has assignment got into the db?
        assignmentCount = self.db.query(models.GroupMembership).count()
        self.assertEquals(assignmentCount, 1)

        #can we see the assignment from outside?
        memberships = self.api.get("/groupmemberships", status_code=200)
        self.assertEquals(len(memberships.json['_items']), 1)
        self.assertEquals(memberships.json['_items'][0]['user_id'], userid)
        self.assertEquals(memberships.json['_items'][0]['group_id'], groupid)

    def test_b_EventSignup(self):
        #make new event
        start = dt.datetime.today() + dt.timedelta(days=2)
        event = self.api.post("/events", data={
            'title': "Awesome Test Event",
            'time_start': start,
            'is_public': True,
            'price': 0,
            'spots': 10,
            'time_register_start': dt.datetime.now(),
            'time_regsiter_end': start,
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

        #Sign up user 1 without departement
        signup = self.api.post("/signups", data={
            'event_id': eventid,
            'user_id': 1,
        }, status_code=422)
        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 0)

        #sign up user 1 to wrong event
        signup = self.api.post("/signups", data={
            'event_id': eventid + 10,
            'user_id': 1,
        }, status_code=422)
        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 0)

        #sign up user 1 with wrong departement
        signup = self.api.post("/signups", data={
            'event_id': eventid,
            'user_id': 1,
            'additional_data': "{'departement': 'INFK'}"
        }, status_code=422)
        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 0)

        #sign up user 1 and do everything right
        signup = self.api.post("/signups", data={
            'event_id': eventid,
            'user_id': 1,
            'additional_data': "{'departement': 'ITET'}",
        }, status_code=201)
        signup1 = signup.json['id']

        signupCount = self.db.query(models.EventSignup).count()
        self.assertEquals(signupCount, 1)

        signups = self.api.get("/signups", status_code=200)
        self.assertEquals(signups.json['_items'][signup1]['event_id'], eventid)
        self.assertEquals(
            signups.json['_items'][signup1]['email'],
            "max-muster@example.net"
        )

        #sign up hermanthegerman@amiv.ethz.ch
        signup = self.api.post("/signups", data={
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
