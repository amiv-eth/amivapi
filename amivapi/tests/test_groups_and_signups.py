# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class GroupTest(util.WebTest):
    """ Test group functionality.
    Group visibility and signup
    adding additional addresses only by moderator and admin
    """

    def test_group_visibility_filter(self):
        """ Test visibility for groups with and without
        allow_self_enrollment
        Test if all usages of GET work
        """
        # Generate three users, one will be mod of the closed group
        # And one group admin
        moderator = self.new_user()
        mod_token = self.new_session(user_id=moderator.id).token
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token
        admin = self.new_user()
        admin_token = self.new_session(user_id=admin.id).token

        # Create groups
        open_group = self.new_group(allow_self_enrollment=True)
        mod_group = self.new_group(allow_self_enrollment=False,
                                   moderator_id=moderator.id)
        admin_group = self.new_group(
            allow_self_enrollment=False,
            permissions={
                'groups': {'GET': True}
            })
        self.new_group_user_member(user_id=admin.id,
                                   group_id=admin_group.id)

        # User can see only the group which allows self enrollment
        user_get = self.api.get("/groups", token=user_token).json
        self.assertTrue(len(user_get["_items"]) == 1)
        self.assertTrue(user_get["_items"][0]["id"] == open_group.id)

        # Furthermore GET on the closed group return 404 (and works on
        # the open group)
        # All other methods are not permitted for registered users
        self.api.get("/groups/%i" % open_group.id, token=user_token,
                     status_code=200)
        self.api.get("/groups/%i" % mod_group.id, token=user_token,
                     status_code=404)
        self.api.get("/groups/%i" % admin_group.id, token=user_token,
                     status_code=404)

        # Moderator can see the open group as well as the group he is in
        mod_get = self.api.get("/groups", token=mod_token).json
        self.assertTrue(len(mod_get["_items"]) == 2)
        self.api.get("/groups/%i" % open_group.id, token=mod_token,
                     status_code=200)
        self.api.get("/groups/%i" % mod_group.id, token=mod_token,
                     status_code=200)
        self.api.get("/groups/%i" % admin_group.id, token=user_token,
                     status_code=404)

        # Admin just gets it
        mod_get = self.api.get("/groups", token=admin_token).json
        self.assertTrue(len(mod_get["_items"]) == 3)
        self.api.get("/groups/%i" % open_group.id, token=admin_token,
                     status_code=200)
        self.api.get("/groups/%i" % mod_group.id, token=admin_token,
                     status_code=200)
        self.api.get("/groups/%i" % admin_group.id, token=admin_token,
                     status_code=200)

    def test_group_signup(self):
        """ Test to create a group user member as the user, the group
        moderate and as group_user_members admin
        """
        moderator = self.new_user()
        mod_token = self.new_session(user_id=moderator.id).token
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token
        admin = self.new_user()
        admin_token = self.new_session(user_id=admin.id).token
        admin_group = self.new_group(
            allow_self_enrollment=False,
            permissions={
                'groupusermembers': {'POST': True, 'DELETE': True}
            })
        self.new_group_user_member(user_id=admin.id,
                                   group_id=admin_group.id)

        group = self.new_group(allow_self_enrollment=True,
                               moderator_id=moderator.id)

        # add non-existing user
        self.api.post("/groupusermembers", data={
            'user_id': -42,
            'group_id': group.id,
        }, token=user_token, status_code=422)

        # add other user that exists, should also not be possible
        self.api.post("/groupusermembers", data={
            'user_id': moderator.id,
            'group_id': group.id,
        }, token=user_token, status_code=422)

        # add to non-existing group
        self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': -42,
        }, token=user_token, status_code=422)

        # group without self enrollment
        self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': admin_group.id,
        }, token=user_token, status_code=422)

        # do everything right
        signup = self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group.id,
        }, token=user_token, status_code=201).json

        # Now test that mod and admin can add and remove any member
        self.api.delete("/groupusermembers/%i" % signup['id'],
                        token=mod_token, status_code=204,
                        headers={'If-Match': signup['_etag']})

        signup_2 = self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group.id,
        }, token=mod_token, status_code=201).json

        self.api.delete("/groupusermembers/%i" % signup_2['id'],
                        token=admin_token, status_code=204,
                        headers={'If-Match': signup_2['_etag']})

        self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group.id,
        }, token=admin_token, status_code=201)

    def test_additional_addresses(self):
        """ Test that mods and admins can add additional addresses to groups
        (and normal users cant, even if they are group members)
        """
        moderator = self.new_user()
        mod_token = self.new_session(user_id=moderator.id).token
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token
        admin = self.new_user()
        admin_token = self.new_session(user_id=admin.id).token
        admin_group = self.new_group(
            allow_self_enrollment=False,
            permissions={
                'forwardaddresses': {'POST': True, 'DELETE': True}
            })
        self.new_group_user_member(user_id=admin.id,
                                   group_id=admin_group.id)

        mod_group = self.new_group(allow_self_enrollment=True,
                                   moderator_id=moderator.id)

        data_mod = {
            "group_id": mod_group.id,
            "address": "some@thing.ch"
        }

        data_admin = {
            "group_id": admin_group.id,
            "address": "some@thing.ch"
        }

        # User cant even
        self.api.post("/forwardaddresses", data=data_mod,
                      token=user_token, status_code=422)

        self.api.post("/forwardaddresses", data=data_admin,
                      token=user_token, status_code=422)

        # User cant see the addresses
        test_address = self.new_forward_address(group_id=mod_group.id)
        self.api.delete("/forwardaddresses/%i" % test_address.id,
                        token=user_token, status_code=404)

        # Even if member
        self.new_group_user_member(user_id=user.id, group_id=mod_group.id)
        self.api.post("/forwardaddresses", data=data_mod,
                      token=user_token, status_code=422)
        # Still cant see it
        self.api.delete("/forwardaddresses/%i" % test_address.id,
                        token=user_token, status_code=404,
                        headers={'If-Match': test_address._etag})

        # Mod can do (only own group)
        mod_address = self.api.post("/forwardaddresses", data=data_mod,
                                    token=mod_token, status_code=201).json

        self.api.post("/forwardaddresses", data=data_admin,
                      token=mod_token, status_code=422)

        self.api.delete("/forwardaddresses/%i" % mod_address["id"],
                        token=mod_token, status_code=204,
                        headers={'If-Match': mod_address['_etag']})

        # Cant see admin group -> 404 when trying to delete
        test_admin_address = self.new_forward_address(group_id=admin_group.id)
        self.api.delete("/forwardaddresses/%i" % test_admin_address.id,
                        token=mod_token, status_code=404,
                        headers={'If-Match': test_admin_address._etag})

        # Admin can do it all
        mod_address = self.api.post("/forwardaddresses", data=data_mod,
                                    token=admin_token, status_code=201).json

        self.api.delete("/forwardaddresses/%i" % mod_address['id'],
                        token=admin_token, status_code=204,
                        headers={'If-Match': mod_address['_etag']})

        self.api.delete("/forwardaddresses/%i" % test_admin_address.id,
                        token=admin_token, status_code=204,
                        headers={'If-Match': test_admin_address._etag})

        self.api.post("/forwardaddresses", data=data_admin,
                      token=admin_token, status_code=201)

    def test_group_id_validation_message(self):
        """ For security reasons it should not be possible to misuse the
        validator of group_signups to find groups you would not see with GET
        The validation response for non-visible and non-existing groups must
        be equal

        The same goes for forwardaddresses
        """
        user = self.new_user()
        token = self.new_session(user_id=user.id).token

        # Group without self enrollment
        group_id = self.new_group(allow_self_enrollment=False).id

        error_1 = self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group_id},
            token=token, status_code=422).json

        error_2 = self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group_id + 1},  # Nonexisting group
            token=token, status_code=422).json

        # The errors must have the same message
        self.assertEquals(error_1['_issues']['group_id'],
                          u"value '%i' must exist in resource 'groups', field"
                          u" 'id'." % group_id)
        self.assertEquals(error_2['_issues']['group_id'],
                          u"value '%i' must exist in resource 'groups', field"
                          u" 'id'." % (group_id + 1))

        error_3 = self.api.post("/forwardaddresses", data={
            'address': "some@address",
            'group_id': group_id},
            token=token, status_code=422).json

        error_4 = self.api.post("/forwardaddresses", data={
            'address': "some@address",
            'group_id': group_id + 1},  # Nonexisting group
            token=token, status_code=422).json

        # The errors must have the same message
        self.assertEquals(error_3['_issues']['group_id'],
                          u"value '%i' must exist in resource 'groups', field"
                          u" 'id'." % group_id)
        self.assertEquals(error_4['_issues']['group_id'],
                          u"value '%i' must exist in resource 'groups', field"
                          u" 'id'." % (group_id + 1))

    def test_signup_and_address_visibility(self):
        """ Visibility of groupusermember and forwardaddress

        Users can only see their memberships and no forwardaddresses
        moderator all signups to his groups as well as the forwardaddresses
        admin all
        """
        user_1 = self.new_user()
        user_1_token = self.new_session(user_id=user_1.id).token
        user_2 = self.new_user()
        moderator = self.new_user()
        mod_token = self.new_session(user_id=moderator.id).token
        admin = self.new_user()
        admin_token = self.new_session(user_id=admin.id).token
        admin_group = self.new_group(
            allow_self_enrollment=False,
            permissions={'forwardaddresses': {'GET': True},
                         'groupusermembers': {'GET': True}})
        self.new_group_user_member(user_id=admin.id,
                                   group_id=admin_group.id)

        # Add some groups
        group = self.new_group()
        mod_group = self.new_group(moderator_id=moderator.id)

        # Add user two to both groups, user 1 to moderated group
        signup_1 = self.new_group_user_member(user_id=user_1.id,
                                              group_id=mod_group.id)
        signup_2 = self.new_group_user_member(user_id=user_2.id,
                                              group_id=mod_group.id)
        signup_3 = self.new_group_user_member(user_id=user_2.id,
                                              group_id=group.id)
        # A forwardaddress for both groups
        self.new_forward_address(group_id=group.id)
        self.new_forward_address(group_id=mod_group.id)

        # Membership visibility
        # User 1 can only see his signup, not other signups in his group,
        # nor signups to other groups
        user_1_get = self.api.get("/groupusermembers", token=user_1_token,
                                  status_code=200).json
        self.assertTrue(len(user_1_get['_items']) == 1)
        self.api.get("/groupusermembers/%i" % signup_1.id,
                     token=user_1_token, status_code=200)
        self.api.get("/groupusermembers/%i" % signup_2.id,
                     token=user_1_token, status_code=404)
        self.api.get("/groupusermembers/%i" % signup_3.id,
                     token=user_1_token, status_code=404)

        # Mod can see both in his group
        mod_get = self.api.get("/groupusermembers", token=mod_token,
                               status_code=200).json
        self.assertTrue(len(mod_get['_items']) == 2)
        self.api.get("/groupusermembers/%i" % signup_1.id,
                     token=mod_token, status_code=200)
        self.api.get("/groupusermembers/%i" % signup_2.id,
                     token=mod_token, status_code=200)
        self.api.get("/groupusermembers/%i" % signup_3.id,
                     token=mod_token, status_code=404)

        # Admin can see all
        admin_get = self.api.get("/groupusermembers", token=admin_token,
                                 status_code=200).json

        # len is actually 4, not three (because the admin himself is member in
        # the admin group, too)
        self.assertTrue(len(admin_get['_items']) == 4)
        self.api.get("/groupusermembers/%i" % signup_1.id,
                     token=admin_token, status_code=200)
        self.api.get("/groupusermembers/%i" % signup_2.id,
                     token=admin_token, status_code=200)
        self.api.get("/groupusermembers/%i" % signup_3.id,
                     token=admin_token, status_code=200)


class GroupNoAuthTests(util.WebTestNoAuth):

    def test_unique_signup(self):
        """Tests that you can signup the same user for the same group only
        once, but other user to the same group and the same user to other
        groups
        """
        user_1 = self.new_user()
        user_2 = self.new_user()

        group_1 = self.new_group()
        group_2 = self.new_group()

        # Signup twice, second should give validation error, since fields
        # are wrong
        self.api.post("/groupusermembers", data={
            "user_id": user_1.id, "group_id": group_1.id},
            status_code=201)
        self.api.post("/groupusermembers", data={
            "user_id": user_1.id, "group_id": group_1.id},
            status_code=422)

        # Other group und other user work fine
        self.api.post("/groupusermembers", data={
            "user_id": user_1.id, "group_id": group_2.id},
            status_code=201)
        self.api.post("/groupusermembers", data={
            "user_id": user_2.id, "group_id": group_1.id},
            status_code=201)
