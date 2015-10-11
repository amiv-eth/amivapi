# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi import models
from amivapi.tests import util


class GroupUserMemberAuthTest(util.WebTest):

    def test_group_user_member_permissions_GET(self):
        """ Test GET permissions for GroupUserMember objects """
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        self.new_group_user_member(group_id=group.id,
                                   user_id=entry_user.id)

        usermembers = self.api.get("/groupusermembers",
                                   token=admin_session.token,
                                   status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(usermembers, "user_id", entry_user.id)
                        is not None)

        usermembers = self.api.get("/groupusermembers",
                                   token=group_owner_session.token,
                                   status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(usermembers, "user_id", entry_user.id)
                        is not None)

        usermembers = self.api.get("/groupusermembers",
                                   token=entry_user_session.token,
                                   status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(usermembers, "user_id", entry_user.id)
                        is not None)

        usermembers = self.api.get("/groupusermembers",
                                   token=registered_session.token,
                                   status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(usermembers, "user_id", entry_user.id)
                        is None)

        usermembers = self.api.get("/groupusermembers", status_code=401)

    def test_group_user_member_permissions_POST(self):
        """ Test POST permissions for GroupUserMember objects """
        db = self.app.data.driver.session

        admin = self.new_user()
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
            "user_id": entry_user.id,
            "group_id": group.id
        }

        self.api.post("/groupusermembers", data=data, status_code=401)

        self.api.post("/groupusermembers", data=data,
                      token=registered_session.token,
                      status_code=403)

        # Admin can add user
        new_usermember = self.api.post("/groupusermembers", data=data,
                                       token=admin_session.token,
                                       status_code=201).json

        db.query(models.GroupUserMember).\
            filter_by(id=new_usermember['id']).delete()
        db.commit()

        # Group owner as well
        new_usermember = self.api.post("/groupusermembers", data=data,
                                       token=group_owner_session.token,
                                       status_code=201).json

        db.query(models.GroupUserMember).\
            filter_by(id=new_usermember['id']).delete()
        db.commit()

        # And the user himself, too
        self.api.post("/groupusermembers", data=data,
                      token=entry_user_session.token,
                      status_code=201)

    def test_group_user_member_permissions_PATCH(self):
        """ Test PATCH permissions using a GroupUserMember object """

        # PATCH is not supported for groupusermembers
        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)
        entry_user = self.new_user()

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        group2 = self.new_group(owner_id=group_owner.id, is_public=True)
        groupusermember = self.new_group_user_member(group_id=group.id,
                                                     user_id=entry_user.id)

        # Try changing the group
        data = {
            "group_id": group2.id
        }

        self.api.patch("/groupusermembers/%i" % groupusermember.id, data=data,
                       headers={'If-Match': groupusermember._etag},
                       status_code=405)

        self.api.patch("/groupusermembers/%i" % groupusermember.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': groupusermember._etag},
                       status_code=405)

        self.api.patch("/groupusermembers/%i" % groupusermember.id, data=data,
                       token=group_owner_session.token,
                       headers={'If-Match': groupusermember._etag},
                       status_code=405)

    def test_group_user_member_permissions_PUT(self):
        """ Test PUT permissions using a GroupUserMember object """

        # PUT is not supported for groupusermembers
        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)
        entry_user = self.new_user()

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        group2 = self.new_group(owner_id=group_owner.id, is_public=True)
        groupusermember = self.new_group_user_member(group_id=group.id,
                                                     user_id=entry_user.id)

        # Try changing the group
        data = {
            "user_id": entry_user.id,
            "group_id": group2.id
        }

        self.api.put("/groupusermembers/%i" % groupusermember.id, data=data,
                     headers={'If-Match': groupusermember._etag},
                     status_code=405)

        self.api.put("/groupusermembers/%i" % groupusermember.id, data=data,
                     token=registered_session.token,
                     headers={'If-Match': groupusermember._etag},
                     status_code=405)

        self.api.put("/groupusermembers/%i" % groupusermember.id, data=data,
                     token=group_owner_session.token,
                     headers={'If-Match': groupusermember._etag},
                     status_code=405)

    def test_permissions_DELETE(self):
        """ Test DELETE permissions for GroupUserMember objects """
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        group_owner = self.new_user()
        group_owner_session = self.new_session(user_id=group_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        group = self.new_group(owner_id=group_owner.id, is_public=True)
        groupusermember = self.new_group_user_member(group_id=group.id,
                                                     user_id=entry_user.id)

        self.api.delete("/groupusermembers/%i" % groupusermember.id,
                        headers={'If-Match': groupusermember._etag},
                        status_code=401)

        self.api.delete("/groupusermembers/%i" % groupusermember.id,
                        token=registered_session.token,
                        headers={'If-Match': groupusermember._etag},
                        status_code=404)

        self.api.delete("/groupusermembers/%i" % groupusermember.id,
                        token=group_owner_session.token,
                        headers={'If-Match': groupusermember._etag},
                        status_code=204)

        groupusermember = self.new_group_user_member(user_id=entry_user.id,
                                                     group_id=group.id)

        self.api.delete("/groupusermembers/%i" % groupusermember.id,
                        token=entry_user_session.token,
                        headers={'If-Match': groupusermember._etag},
                        status_code=204)

        groupusermember = self.new_group_user_member(user_id=entry_user.id,
                                                     group_id=group.id)

        self.api.delete("/groupusermembers/%i" % groupusermember.id,
                        token=admin_session.token,
                        headers={'If-Match': groupusermember._etag},
                        status_code=204)
