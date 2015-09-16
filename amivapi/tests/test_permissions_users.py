# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class UsersPermissionsTest(util.WebTest):

    def test_users_permissions_get(self):
        """ Test GET permissions for user objects """
        root_session = self.new_session(user_id=0)

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        users = self.api.get("/users", token=root_session.token,
                             status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(users, "id", owner.id) is not None)

        users = self.api.get("/users", token=admin_session.token,
                             status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(users, "id", owner.id) is not None)

        users = self.api.get("/users", token=owner_session.token,
                             status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(users, "id", owner.id) is not None)

        users = self.api.get("/users", token=registered_session.token,
                             status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(users, "id", owner.id) is None)

        users = self.api.get("/users", status_code=401)

    def test_users_permissions_post(self):
        """ Test POST permissions for user objects """
        root_session = self.new_session(user_id=0)

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        data = {
            "username": "guy",
            "firstname": u"random",
            "lastname": u"guy",
            "email": u"guy@example.com",
            "gender": "male",
            "membership": "none",
        }
        self.api.post("/users", data=data, token=admin_session.token,
                      status_code=201)

        data['username'] = "guy2"
        data['email'] = u"guy2@example.com"
        self.api.post("/users", data=data, token=root_session.token,
                      status_code=201)

        data['username'] = "guy3"
        data['email'] = u"guy3@example.com"
        self.api.post("/users", data=data, token=registered_session.token,
                      status_code=403)

        self.api.post("/users", data=data, status_code=401)

    def test_users_permissions_patch(self):
        """ Test PATCH permissions for user objects """
        root_session = self.new_session(user_id=0)

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        patchdata = {
            "rfid": "777777"
        }
        self.api.patch("/users/%i" % owner.id, data=patchdata,
                       headers={'If-Match': owner._etag}, status_code=401)

        self.api.patch("/users/%i" % owner.id, data=patchdata,
                       token=registered_session.token,
                       headers={'If-Match': owner._etag}, status_code=404)

        self.api.patch("/users/%i" % owner.id, data=patchdata,
                       token=owner_session.token,
                       headers={'If-Match': owner._etag}, status_code=200)

        patchdata = {
            "rfid": "666666"
        }
        self.api.patch("/users/%i" % owner.id, data=patchdata,
                       token=admin_session.token,
                       headers={'If-Match': owner._etag}, status_code=200)

        patchdata = {
            "rfid": "555555"
        }
        self.api.patch("/users/%i" % owner.id, data=patchdata,
                       token=root_session.token,
                       headers={'If-Match': owner._etag}, status_code=200)

    def test_users_permissions_put(self):
        """ Test PUT permissions for user objects """
        root_session = self.new_session(user_id=0)

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        data = {
            'username': 'replacement',
            'password': 'replacement',
            'firstname': 'replacement',
            'lastname': 'replacement',
            'gender': 'female',
            'membership': 'none',
            'email': 'replacement@example.com',
        }

        self.api.put("/users/%i" % owner.id, data=data,
                     headers={'If-Match': owner._etag}, status_code=401)
        self.api.put("/users/%i" % owner.id, data=data,
                     token=registered_session.token,
                     headers={'If-Match': owner._etag}, status_code=403)
        self.api.put("/users/%i" % owner.id, data=data,
                     token=owner_session.token,
                     headers={'If-Match': owner._etag}, status_code=403)
        self.api.put("/users/%i" % owner.id, data=data,
                     token=admin_session.token,
                     headers={'If-Match': owner._etag}, status_code=200)

        # We replaced the owner with something, we need a new owner and data
        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        data = {
            'username': 'replacement2',
            'password': 'replacement2',
            'firstname': 'replacement2',
            'lastname': 'replacement2',
            'gender': 'male',
            'membership': 'none',
            'email': 'replacement2@example.com',
        }

        self.api.put("/users/%i" % owner.id, data=data,
                     token=root_session.token,
                     headers={'If-Match': owner._etag}, status_code=200)

    def test_users_permissions_delete(self):
        """ Test DELETE permissions for user objects """
        root_session = self.new_session(user_id=0)

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        self.api.delete("/users/%i" % owner.id,
                        headers={'If-Match': owner._etag}, status_code=401)
        self.api.delete("/users/%i" % owner.id, token=registered_session.token,
                        headers={'If-Match': owner._etag}, status_code=403)
        self.api.delete("/users/%i" % owner.id, token=owner_session.token,
                        headers={'If-Match': owner._etag}, status_code=403)
        self.api.delete("/users/%i" % owner.id, token=admin_session.token,
                        headers={'If-Match': owner._etag}, status_code=204)

        owner = self.new_user()
        self.api.delete("/users/%i" % owner.id, token=root_session.token,
                        headers={'If-Match': owner._etag}, status_code=204)
