# -*- coding: utf-8 -*-
#
# AMIVAPI test_deletion.py
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
from amivapi import models


class DeletionTests(util.WebTestNoAuth):

    def test_delete_user_to_forwarduser(self):
        user = self.new_user()
        forward = self.new_forward()
        self.new_forward_user(user_id=user.id, forward_id=forward.id)

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': user._etag}, status_code=204)
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 0)
        # We want the forwarduser-entry to be deleted but not the forward
        # itself
        forward_count = self.db.query(models.Forward).count()
        self.assertEquals(forward_count, 1)

    def test_delete_forward_to_forwarduserForwardAddress(self):
        user = self.new_user()
        forward = self.new_forward()
        self.new_forward_user(user_id=user.id, forward_id=forward.id)
        self.new_forward_address(forward_id=forward.id)

        self.api.delete("/forwards/%i" % forward.id,
                        headers={'If-Match': forward._etag}, status_code=204)
        forward_count = self.db.query(models.Forward).count()
        self.assertEquals(forward_count, 0)
        # forwarduser and forwardaddress entries should now be deleted
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 0)
        forwardaddress_count = self.db.query(models.ForwardAddress).count()
        self.assertEquals(forwardaddress_count, 0)

    def test_delete_user_to_permission(self):
        user = self.new_user()
        permission = self.new_permission(user_id=user.id, role='vorstand')

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': permission._etag},
                        status_code=204)
        # We have with ids -1 and 0 2 users left after our user got deleted
        self.assert_count(models.User, 2)
        self.assert_count(models.Permission, 0)

    def test_delete_event_to_signup(self):
        event = self.new_event()
        self.new_signup(event_id=event.id)

        self.api.delete("/events/%i" % event.id,
                        headers={'If-Match': event._etag},
                        status_code=204)
        self.assert_count(models.Event, 0)
        self.assert_count(models.EventSignup, 0)

    def test_delete_user_to_signup(self):
        event = self.new_event()
        user = self.new_user()
        self.new_signup(event_id=event.id, user_id=user.id)

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': user._etag},
                        status_code=204)
        # We have with ids -1 and 0 2 users left after our user got deleted
        self.assert_count(models.User, 2)
        self.assert_count(models.EventSignup, 0)
        # the Event shold still exist
        self.assert_count(models.Event, 1)
