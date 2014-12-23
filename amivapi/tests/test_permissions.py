from amivapi.tests import util
from amivapi import models


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

    def test_forward_users_permissions_GET(self):
        """ Test GET permissions for ForwardUser objects """
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id)
        self.new_forward_user(forward_id=forward.id,
                              user_id=entry_user.id)

        forwards = self.api.get("/forwardusers", token=admin_session.token,
                                status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(forwards, "user_id", entry_user.id)
                        is not None)

        forwards = self.api.get("/forwardusers",
                                token=list_owner_session.token,
                                status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(forwards, "user_id", entry_user.id)
                        is not None)

        forwards = self.api.get("/forwardusers",
                                token=entry_user_session.token,
                                status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(forwards, "user_id", entry_user.id)
                        is not None)

        forwards = self.api.get("/forwardusers",
                                token=registered_session.token,
                                status_code=200).json['_items']
        self.assertTrue(util.find_by_pair(forwards, "user_id", entry_user.id)
                        is None)

        forwards = self.api.get("/forwardusers", status_code=401)

    def test_forward_users_permissions_POST(self):
        """ Test POST permissions for ForwardUser objects """
        db = self.app.data.driver.session

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id)

        data = {
            "user_id": entry_user.id,
            "forward_id": forward.id
        }

        self.api.post("/forwardusers", data=data, status_code=401)

        self.api.post("/forwardusers", data=data,
                      token=registered_session.token,
                      status_code=403)

        new_forward = self.api.post("/forwardusers", data=data,
                                    token=admin_session.token,
                                    status_code=201).json

        db.query(models.ForwardUser).filter_by(id=new_forward['id']).delete()
        db.commit()

        new_forward = self.api.post("/forwardusers", data=data,
                                    token=list_owner_session.token,
                                    status_code=201).json

        db.query(models.ForwardUser).filter_by(id=new_forward['id']).delete()
        db.commit()

        self.api.post("/forwardusers", data=data,
                      token=entry_user_session.token,
                      status_code=201)

    def test_forward_users_permissions_PATCH(self):
        """ Test PATCH permissions for ForwardUser objects """

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id)
        forward2 = self.new_forward(owner_id=list_owner.id)
        forward_user = self.new_forward_user(forward_id=forward.id,
                                             user_id=entry_user.id)

        # Try changing the forward
        data = {
            "forward_id": forward2.id
        }

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       headers={'If-Match': forward_user._etag},
                       status_code=401)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=404)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        forward3 = self.new_forward(owner_id=0)

        data = {
            "forward_id": forward3.id
        }
        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=403)

        data = {
            "forward_id": forward.id
        }
        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        data = {
            "forward_id": forward2.id
        }
        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=admin_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        forward_user.forward_id = forward.id

        # Try changing the user

        entry_owner2 = self.new_user()

        data = {
            "user_id": entry_owner2.id
        }

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       headers={'If-Match': forward_user._etag},
                       status_code=401)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=404)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        forward_user.user_id = entry_user.id

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=403)

    def test_forward_users_permissions_PUT(self):
        """ Test PUT permissions for ForwardUser objects """

        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id)
        forward2 = self.new_forward(owner_id=list_owner.id)
        forward_user = self.new_forward_user(forward_id=forward.id,
                                             user_id=entry_user.id)

        # Try changing the forward
        data = {
            "user_id": entry_user.id,
            "forward_id": forward2.id
        }

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       headers={'If-Match': forward_user._etag},
                       status_code=401)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=404)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        forward3 = self.new_forward(owner_id=0)

        data = {
            "user_id": entry_user.id,
            "forward_id": forward3.id
        }
        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=403)

        data = {
            "user_id": entry_user.id,
            "forward_id": forward.id
        }
        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        data = {
            "user_id": entry_user.id,
            "forward_id": forward2.id
        }
        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=admin_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        # Try changing the user

        entry_user2 = self.new_user()

        data = {
            "user_id": entry_user2.id,
            "forward_id": forward2.id
        }

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       headers={'If-Match': forward_user._etag},
                       status_code=401)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=404)

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=200)

        forward_user.user_id = entry_user.id

        self.api.patch("/forwardusers/%i" % forward_user.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_user._etag},
                       status_code=403)

    def test_forward_users_permissions_DELETE(self):
        """ Test DELETE permissions for ForwardUser objects """
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id)
        forward_user = self.new_forward_user(forward_id=forward.id,
                                             user_id=entry_user.id)

        self.api.delete("/forwardusers/%i" % forward_user.id,
                        headers={'If-Match': forward_user._etag},
                        status_code=401)

        self.api.delete("/forwardusers/%i" % forward_user.id,
                        token=registered_session.token,
                        headers={'If-Match': forward_user._etag},
                        status_code=404)

        self.api.delete("/forwardusers/%i" % forward_user.id,
                        token=list_owner_session.token,
                        headers={'If-Match': forward_user._etag},
                        status_code=200)

        forward_user = self.new_forward_user(user_id=entry_user.id,
                                             forward_id=forward.id)

        self.api.delete("/forwardusers/%i" % forward_user.id,
                        token=entry_user_session.token,
                        headers={'If-Match': forward_user._etag},
                        status_code=200)

        forward_user = self.new_forward_user(user_id=entry_user.id,
                                             forward_id=forward.id)

        self.api.delete("/forwardusers/%i" % forward_user.id,
                        token=admin_session.token,
                        headers={'If-Match': forward_user._etag},
                        status_code=200)
