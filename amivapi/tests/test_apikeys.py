# -*- coding: utf-8 -*-
#
# AMIVAPI test_apikeys.py
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


class APIKeyTest(util.WebTest):

    def test_get_users_with_apikey(self):
        apikey = u"dsfsjkdfsdhkfhsdkfjhsdfjh"
        self.app.config['APIKEYS'][apikey] = {
            'name': 'Testkey',
            'users': {'GET': 1},
        }

        items = self.api.get(
            "/users", token=apikey, status_code=200).json['_items']

        # Can we see the root user?
        self.assertTrue(util.find_by_pair(items, "id", 0) is not None)
