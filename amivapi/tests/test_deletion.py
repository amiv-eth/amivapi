# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util
from amivapi import models, events, groups


class DeletionTests(util.WebTestNoAuth):

    def test_delete_user_to_groupmember(self):
        user = self.new_user()
        group = self.new_group()
        self.new_group_member(user_id=user.id, group_id=group.id)

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': user._etag}, status_code=204)
        groupmember_count = self.db.query(groups.GroupMember).count()
        self.assertEquals(groupmember_count, 0)
        # We want the groupmember-entry to be deleted but not the group
        # itself
        group_count = self.db.query(groups.Group).count()
        self.assertEquals(group_count, 1)

    def test_delete_group_to_groupmember_and_forwards(self):
        user = self.new_user()
        group = self.new_group()
        self.new_group_member(user_id=user.id, group_id=group.id)
        self.new_group_address(group_id=group.id)

        self.api.delete("/groups/%i" % group.id,
                        headers={'If-Match': group._etag}, status_code=204)
        group_count = self.db.query(groups.Group).count()
        self.assertEquals(group_count, 0)
        # groupmember and forwardaddress entries should now be deleted
        groupmember_count = self.db.query(groups.GroupMember).count()
        self.assertEquals(groupmember_count, 0)
        forward_count = (
            self.db.query(groups.GroupAddress).count())
        self.assertEquals(forward_count, 0)

    def test_delete_event_to_signup(self):
        event = self.new_event()
        self.new_signup(event_id=event.id)

        self.api.delete("/events/%i" % event.id,
                        headers={'If-Match': event._etag},
                        status_code=204)
        self.assert_count(events.Event, 0)
        self.assert_count(events.EventSignup, 0)

    def test_delete_user_to_signup(self):
        event = self.new_event()
        user = self.new_user()
        self.new_signup(event_id=event.id, user_id=user.id)

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': user._etag},
                        status_code=204)
        # We have with ids -1 and 0 2 users left after our user got deleted
        self.assert_count(models.User, 2)
        self.assert_count(events.EventSignup, 0)
        # the Event shold still exist
        self.assert_count(events.Event, 1)
