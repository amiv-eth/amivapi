# -*- coding: utf-8 -*-
#
# AMIVAPI test_session.py
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

from amivapi.tests import util


class SessionResourceTest(util.WebTest):

    def test_create_session(self):
        """ Test to obtain a login token """
        password = u"some-really-secure-password"
        user = self.new_user(password=password)

        self.api.post("/sessions", data={
            'username': user.username,
            'password': password,
        }, status_code=201)

    def test_wrong_password(self):
        """ Test to login with a wrong password """
        user = self.new_user(password=u"something")

        self.api.post("/sessions", data={
            'username': user.username,
            'password': u"something-else",
        }, status_code=401)

    def test_delete_session(self):
        """ Test to logout """
        password = u"awesome-password"
        user = self.new_user(password=password)

        session = self.new_session(user_id=user.id)

        # Check if the user is logged in
        self.api.get("/sessions", token=session.token, status_code=200)

        self.api.delete("/sessions/%i" % session.id, token=session.token,
                        headers={'If-Match': session._etag}, status_code=204)

        # Check if still logged in
        self.api.get("/sessions", session.token, status_code=401)
