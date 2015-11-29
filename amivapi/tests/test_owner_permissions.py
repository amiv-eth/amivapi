# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class OwnerPermissionsTest(util.WebTest):
    """ This test ensures that the different types of ownership work. """

    def test_group_owners(self):
        """ groups have a rather complex owner system.
        The moderator and all members of the group are owners
        A groupmembership is owned by the user in question as well as by
        the group owner
        The only thing owners can do is GET
        """

        # Create two users, one will be group moderator, the other a member
        moderator = self.new_user()
        mod_token = self.new_session(user_id=moderator.id).token
        member = self.new_user()
        mem_token = self.new_session(user_id=member.id).token

        # Create a group without self-enrollment
        group = self.new_group(allow_self_enrollment=False,
                               moderator_id=moderator.id)

        # Moderator can see the group, member not
        self.api.get("/groups/%i" % group.id, token=mod_token,
                     status_code=200)
        self.api.get("/groups/%i" % group.id, token=mem_token,
                     status_code=404)

        # let the second user join the group
        membership = self.new_group_user_member(user_id=member.id,
                                                group_id=group.id)

        # Group is visible by member now
        self.api.get("/groups/%i" % group.id, token=mem_token,
                     status_code=200)

        # Groupmembership visible by moderator and member (both owners)
        self.api.get("/groupusermembers/%i" % membership.id, token=mod_token,
                     status_code=200)
        self.api.get("/groupusermembers/%i" % membership.id, token=mem_token,
                     status_code=200)

        # Additionally, owners of the membership can delete it.
        # Ensure that both mod and member can delete
        self.api.delete("/groupusermembers/%i" % membership.id,
                        token=mod_token,
                        headers={'If-Match': membership._etag},
                        status_code=204)

        # Recreate
        membership = self.new_group_user_member(user_id=member.id,
                                                group_id=group.id)

        self.api.delete("/groupusermembers/%i" % membership.id,
                        token=mem_token,
                        headers={'If-Match': membership._etag},
                        status_code=204)
