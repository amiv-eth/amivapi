# -*- coding: utf-8 -*-
#
# AMIVAPI test_permission_matrix.py
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


class PermissionMatrixTest(util.WebTest):

    def test_vorstand_role(self):
        user = self.new_user()
        self.new_permission(user_id=user.id, role="vorstand")
        token = self.new_session(user_id=user.id).token

        self.api.get("/joboffers", token=token, status_code=200)

        data = {
            "company": "Conrad AG"
        }
        of = self.api.post("/joboffers", token=token, data=data,
                           status_code=201).json

        of = self.api.patch("/joboffers/%i" % of['id'],
                            headers={"If-Match": of['_etag']},
                            token=token,
                            data=data,
                            status_code=200).json

        of = self.api.put("/joboffers/%i" % of['id'],
                          headers={"If-Match": of['_etag']},
                          token=token,
                          data=data,
                          status_code=200).json

        self.api.delete("/joboffers/%i" % of['id'],
                        headers={"If-Match": of['_etag']},
                        token=token,
                        status_code=204)

    def test_event_admin_role(self):
        user = self.new_user()
        self.new_permission(user_id=user.id, role="event_admin")
        token = self.new_session(user_id=user.id).token

        self.api.get("/joboffers", token=token, status_code=200)

        data = {
            "company": "no"
        }
        self.api.post("/joboffers", token=token, data=data,
                      status_code=403)

        of = self.new_joboffer()

        self.api.patch("/joboffers/%i" % of.id,
                       token=token,
                       headers={"If-Match": of._etag},
                       data=data,
                       status_code=403)

        self.api.put("/joboffers/%i" % of.id,
                     token=token,
                     headers={"If-Match": of._etag},
                     data=data,
                     status_code=403)

        self.api.delete("/joboffers/%i" % of.id,
                        token=token,
                        headers={"If-Match": of._etag},
                        status_code=403)
