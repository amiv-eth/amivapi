# -*- coding: utf-8 -*-
#
# AMIVAPI test_public_forward.py
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


class PublicForwardTest(util.WebTest):

    def test_self_enroll_public_forward(self):
        user = self.new_user()
        forward = self.new_forward(is_public=True)
        session = self.new_session(user_id=user.id)

        self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward.id,
        }, token=session.token, status_code=201)

        forward2 = self.new_forward(is_public=False)

        self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward2.id,
        }, token=session.token, status_code=403)
