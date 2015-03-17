# -*- coding: utf-8 -*-
#
# AMIVAPI test_hidden_passwords.py
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


class TestHiddenPasswords(util.WebTestNoAuth):

    def test_passwords_hidden(self):
        user = self.new_user()

        response = self.api.get("/users/%i" % user.id,
                                status_code=200)

        self.assertTrue('password' not in response.json)

        response = self.api.get("/users/%i" % user.id,
                                query_string='projection={"password":1}',
                                status_code=403)
