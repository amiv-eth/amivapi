from amivapi.tests import util


class PermissionsTest(util.WebTest):

    def test_users_permissions(self):
        """ Test endpoint permissions for user objects """
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        """ Test GET """

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

        """ Test POST """

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
        self.api.post("/users", data=data, token=registered_session.token,
                      status_code=403)

        self.api.post("/users", data=data, status_code=401)

        """ Test PATCH """

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

        self.api.patch("/users/%i" % owner.id, data=patchdata,
                       token=admin_session.token,
                       headers={'If-Match': owner._etag}, status_code=200)

        """ Test PUT """

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

        # We replaced the owner with something, we need a new owner
        owner = self.new_user()
        owner_session = self.new_session(user_id=owner.id)

        """ Test DELETE """

        self.api.delete("/users/%i" % owner.id,
                        headers={'If-Match': owner._etag}, status_code=401)
        self.api.delete("/users/%i" % owner.id, token=registered_session.token,
                        headers={'If-Match': owner._etag}, status_code=403)
        self.api.delete("/users/%i" % owner.id, token=owner_session.token,
                        headers={'If-Match': owner._etag}, status_code=403)
        self.api.delete("/users/%i" % owner.id, token=admin_session.token,
                        headers={'If-Match': owner._etag}, status_code=200)
