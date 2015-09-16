# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class GroupAdressMemberAuthTest(util.WebTest):

    def test_groupaddressmember_permissions_GET(self):
        """ Test GET permissions for GroupAddressMember objects """
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        self.new_group_address_member(group_id=group.id,
                                      email=email)

        self.api.get("/groupaddressmembers", token=admin_session.token,
                     status_code=200)

        self.api.get("/groupaddressmembers",
                     token=group_owner_session.token,
                     status_code=200).json

        # groupaddressmembers should just be visible for admin and owner
        response = self.api.get("/groupaddressmembers",
                                token=registered_session.token,
                                status_code=200).json
        self.assertEquals(len(response['_items']), 0)

        self.api.get("/groupaddressmembers", status_code=401)

    def test_groupaddressmember_permissions_POST(self):
        """ Test POST permissions for GroupAddressMember objects """
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)

        data = {
            "email": email,
            "group_id": group.id
        }

        self.api.post("/groupaddressmembers", data=data, status_code=202)

        self.api.post("/groupaddressmembers", data=data,
                      token=registered_session.token,
                      status_code=202)

        self.api.post("/groupaddressmembers", data=data,
                      token=entry_user_session.token,
                      status_code=202)

        self.api.post("/groupaddressmembers", data=data,
                      token=admin_session.token,
                      status_code=202).json

        self.api.post("/groupaddressmembers", data=data,
                      token=group_owner_session.token,
                      status_code=202).json

    def test_groupaddressmember_permissions_PATCH(self):
        """ Test PATCH permissions for GroupAddressMember objects """

        # PATCH is not allowed for /groupaddressmembers nor items
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        group2 = self.new_group(owner_id=group_owner.id, is_public=True)
        groupaddressmember = self.new_group_address_member(
            group_id=group.id,
            email=email)

        # Try changing the group
        data = {
            "group_id": group2.id
        }

        self.api.patch("/groupaddressmembers/%i" % groupaddressmember.id,
                       data=data,
                       headers={'If-Match': groupaddressmember._etag},
                       status_code=405)

        self.api.patch("/groupaddressmembers/%i" % groupaddressmember.id,
                       data=data,
                       token=registered_session.token,
                       headers={'If-Match': groupaddressmember._etag},
                       status_code=405)

        self.api.patch("/groupaddressmembers/%i" % groupaddressmember.id,
                       data=data,
                       token=group_owner_session.token,
                       headers={'If-Match': groupaddressmember._etag},
                       status_code=405)

    def test_group_address_member_permissions_PUT(self):
        """ Test PUT permissions using a GroupAddressMember object """

        # PUT is not supported for groupaddressmembers
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        group2 = self.new_group(owner_id=group_owner.id, is_public=True)
        groupaddressmember = self.new_group_address_member(group_id=group.id,
                                                           email=email)

        # Try changing the group
        data = {
            "email": email,
            "group_id": group2.id
        }

        self.api.put("/groupaddressmembers/%i" % groupaddressmember.id,
                     data=data,
                     headers={'If-Match': groupaddressmember._etag},
                     status_code=405)

        self.api.put("/groupaddressmembers/%i" % groupaddressmember.id,
                     data=data,
                     token=registered_session.token,
                     headers={'If-Match': groupaddressmember._etag},
                     status_code=405)

        self.api.put("/groupaddressmembers/%i" % groupaddressmember.id,
                     data=data,
                     token=group_owner_session.token,
                     headers={'If-Match': groupaddressmember._etag},
                     status_code=405)

    def test_permissions_DELETE(self):
        """ Test DELETE permissions for GroupAddressMember objects """
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        groupaddressmember = self.new_group_address_member(group_id=group.id,
                                                           email=email)

        # try to delete without token - 403
        self.api.delete("/groupaddessmembers/%i" % groupaddressmember.id,
                        headers={'If-Match': groupaddressmember._etag},
                        status_code=404)

        # try to delete, but you are not allowed without confirmation-token
        self.api.delete("/groupaddressmembers/%i" % groupaddressmember.id,
                        token=registered_session.token,
                        headers={'If-Match': groupaddressmember._etag},
                        status_code=403)

        # delete as list_owner is allowed
        self.api.delete("/groupaddressmembers/%i" % groupaddressmember.id,
                        token=group_owner_session.token,
                        headers={'If-Match': groupaddressmember._etag},
                        status_code=204)

        # delete with the token send by email is also allowed
        groupaddressmember = self.new_group_address_member(group_id=group.id,
                                                           email=email)
        self.api.delete("/groupaddressmembers/%i" % groupaddressmember.id,
                        headers={'If-Match': groupaddressmember._etag,
                                 'Token': groupaddressmember._token},
                        status_code=204)

        # delete as an admin works always
        groupaddressmember = self.new_group_address_member(email=email,
                                                           group_id=group.id)

        self.api.delete("/groupaddressmembers/%i" % groupaddressmember.id,
                        token=admin_session.token,
                        headers={'If-Match': groupaddressmember._etag},
                        status_code=204)
