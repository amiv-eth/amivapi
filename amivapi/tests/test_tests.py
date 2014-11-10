from amivapi import models
from amivapi.tests import util


class IsolationTest(util.WebTest):
    """Test isolation between tests.

    The naming of the test methods is important here, because nose by default
    will pick them up (and execute) in alphabetical order.
    """

    def test_a(self):
        """Adding data to the database works."""
        self.assertEquals(self.db.identity_map, {})

        user = models.User(username=u"test-user",
                           firstname=u"John",
                           lastname=u"Smith",
                           email=u"testuser-1@example.net",
                           gender="male")
        self.db.add(user)
        self.db.flush()

        # The data is added to the database
        users = self.db.query(models.User).all()
        self.assertEquals(len(users), 1)
        self.assertEquals(users[0], user)

        # The data is also visible from the API
        resp = self.api.get("/users", status_code=200)
        self.assertEquals(len(resp.json['_items']), 1)

        userid = resp.json['_items'][0]['id']
        self.assertEquals(userid, user.id)

        resp = self.api.get("/users/%i" % userid, status_code=200)
        self.assertEquals(resp.json['id'], userid)

    def test_b(self):
        """No data from test_a has survived."""
        # The session is empty again, and the user has not been persisted.
        self.assertEquals(self.db.identity_map, {})
        users = self.db.query(models.User).all()
        self.assertEquals(len(users), 0)

        # The API also does not return users anymore
        resp = self.api.get("/users", status_code=200)
        self.assertEquals(len(resp.json['_items']), 0)
