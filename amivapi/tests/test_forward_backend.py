# -*- coding: utf-8 -*-
#
# AMIVAPI test_forward_backend.py
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

from os.path import exists

from amivapi.tests import util


class ForwardBackendTest(util.WebTestNoAuth):

    def test_forward_creation(self):
        session = self.new_session()
        user = self.new_user(email=u"test@no.no")
        user2 = self.new_user(email=u"looser92@gmx.com")

        forward = self.new_forward(address=u"test", is_public=True)

        fuser = self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward.id,
        }, token=session.token, status_code=201).json

        path = self.app.config['FORWARD_DIR'] + "/.forward+" + forward.address
        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "test@no.no\n")

        self.api.post("/forwardusers", data={
            'forward_id': forward.id,
            'user_id': user2.id,
        }, token=session.token, status_code=201).json

        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "test@no.no\nlooser92@gmx.com\n")

        self.api.delete("/forwardusers/%i" % fuser['id'],
                        token=session.token,
                        headers={"If-Match": fuser['_etag']},
                        status_code=204)

        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "looser92@gmx.com\n")

        self.api.delete("/forwards/%i" % forward.id,
                        token=session.token,
                        headers={"If-Match": forward._etag},
                        status_code=204)

        self.assertTrue(exists(path) is False)
