# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi import models
from amivapi.tests import util


class IsolationTest(util.WebTestNoAuth):
    """Test isolation between tests.

    The naming of the test methods is important here, because nose by default
    will pick them up (and execute) in alphabetical order.
    """

    def test_a(self):
        """Adding data to the database works."""
        # Check that there is no previous data
        self.assertFalse(self.db.identity_map)

        session = models.Session(user_id=0,
                                 token="test",
                                 _author=0)
        self.db.add(session)
        self.db.flush()

        # The data is added to the database
        sessions = self.db.query(models.Session).all()
        self.assertEquals(len(sessions), 1)
        self.assertEquals(sessions[0], session)

        # The data is also visible from the API
        resp = self.api.get("/sessions", status_code=200)
        self.assertEquals(len(resp.json['_items']), 1)

        sessionid = resp.json['_items'][0]['id']
        self.assertEquals(sessionid, session.id)

        resp = self.api.get("/sessions/%i" % sessionid, status_code=200)
        self.assertEquals(resp.json['id'], sessionid)

    def test_b(self):
        """No data from test_a has survived."""
        # The session is empty again, and the user has not been persisted.
        self.assertFalse(self.db.identity_map)
        sessions = self.db.query(models.Session).all()
        self.assertEquals(len(sessions), 0)

        # The API also does not return users anymore
        resp = self.api.get("/sessions", status_code=200)
        self.assertEquals(len(resp.json['_items']), 0)

    def test_testrelations(self):
        """ Check whether relations can be resolved with the test database
        system and get is updated with new data """

        user = self.new_user()
        self.new_session(user_id=user.id)
        self.api.get("/users/%i?projection={\"sessions\":1}" % user.id,
                     status_code=200)
        self.new_session(user_id=user.id)

        resp = self.api.get("/users/%i?projection={\"sessions\":1}" % user.id,
                            status_code=200).json

        self.assertEqual(len(resp["sessions"]), 2)
