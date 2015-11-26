# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi import models
from amivapi.tests import util


class GroupTest(util.WebTest):
    """ Test group functionality.
    Group visibility and signup
    adding additional addresses only by moderator and admin
    """

    def test_group_signup(self):
        """ Test signup for groups with and without self allow_self_enrollment
        """
        # Generate two users, one will be mod of the closed group
        moderator = self.new_user()
        mod_token = self.new_session(user_id=moderator.id).token
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token

        # Create groups
        open_group = self.new_group(allow_self_enrollment=True)
        closed_group = self.new_group(allow_self_enrollment=False,
                                      moderator_id=moderator.id)

        print("HEEEEREEE")

        # User can see only the group which allows self enrollment
        user_get = self.api.get("/groups", token=user_token).json
        self.assertTrue(len(user_get["_items"]) == 1)
        self.assertTrue(user_get["_items"][0]["id"] == open_group.id)

        # Moderator can see the open group as well as the group he is in
        user_get = self.api.get("/groups", token=mod_token).json
        self.assertTrue(len(user_get["_items"]) == 2)


    def group_addresses(self):
        return


    def redo_everthing(self):
        """Remind me that its not done

        What to do:
        group visibility,
        group membership
        """
        return

    def test_assign_registered(self):
        return
        user = self.new_user()
        group = self.new_group(allow_self_enrollment=True)

        # add non-existing user
        self.api.post("/groupusermembers", data={
            'user_id': user.id + 1,
            'group_id': group.id,
        }, status_code=422)
        self.assert_count(models.GroupUserMember, 0)

        # add to non-existing group
        self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group.id + 1,
        }, status_code=422)
        self.assert_count(models.GroupUserMember, 0)

        # do everything right
        self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group.id,
        }, status_code=201)
        self.assert_count(models.GroupUserMember, 1)

    def test_assign_unregistered(self):
        return
        email = "test-mail@amiv.ethz.ch"
        group = self.new_group(allow_self_enrollment=True)

        # add non-email-address
        self.api.post("/groupaddressmembers", data={
            'email': 'fakeaddress',
            'group_id': group.id,
        }, status_code=422)
        self.assert_count(models.GroupAddressMember, 0)

        # add to not existing group
        self.api.post("/groupaddressmembers", data={
            'email': email,
            'group_id': group.id + 1,
        }, status_code=422)
        self.assert_count(models.GroupAddressMember, 0)

        # do everything right and look if it get's added to Confirm
        self.api.post("/groupaddressmembers", data={
            'email': email,
            'group_id': group.id,
        }, status_code=202)
        self.assert_count(models.GroupAddressMember, 1)
        membership = self.db.query(models.GroupAddressMember).first()
        self.assertEquals(membership._confirmed, False)

        token = membership._token
        self.api.post("/confirmations", data={
            'token': token
        }, status_code=201).json
        self.assertEquals(membership._confirmed, True)

        # try to delete it again
        self.api.delete("/groupaddressmembers/%i" % membership.id,
                        headers={'If-Match': membership._etag,
                                 'Token': token},
                        status_code=204)
        self.assert_count(models.GroupAddressMember, 0)
