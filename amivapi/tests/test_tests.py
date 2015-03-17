# -*- coding: utf-8 -*-
#
# AMIVAPI test_tests.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from amivapi import models
from amivapi.tests import util


class IsolationTest(util.WebTestNoAuth):
    """Test isolation between tests.

    The naming of the test methods is important here, because nose by default
    will pick them up (and execute) in alphabetical order.
    """

    def test_a(self):
        """Adding data to the database works."""
        self.assertEquals(self.db.identity_map, {})

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
        self.assertEquals(self.db.identity_map, {})
        sessions = self.db.query(models.Session).all()
        self.assertEquals(len(sessions), 0)

        # The API also does not return users anymore
        resp = self.api.get("/sessions", status_code=200)
        self.assertEquals(len(resp.json['_items']), 0)
