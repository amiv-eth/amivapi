from amivapi import models
from amivapi.tests import util


class ForwardTest(util.WebTestNoAuth):

    def test_assign_registered(self):
        user = self.new_user()
        forward = self.new_forward(is_public=True)

        # forward non-existing user
        self.api.post("/forwardusers", data={
            'user_id': user.id + 1,
            'forward_id': forward.id,
        }, status_code=422)
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 0)

        # forward non-existing forward
        self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward.id + 1,
        }, status_code=422)
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 0)

        # do everything right
        self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward.id,
        }, status_code=201)
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 1)

    def test_assign_unregistered(self):
        email = "test-mail@amiv.ethz.ch"
        forward = self.new_forward(is_public=True)

        # forward to non-email-address
        self.api.post("/forwardaddresses", data={
            'email': 'fakeaddress',
            'forward_id': forward.id,
        }, status_code=422)
        forwards = self.db.query(models.ForwardAddress)
        self.assertEquals(forwards.count(), 0)

        # forwards to not existing forward
        self.api.post("/forwardaddresses", data={
            'email': email,
            'forward_id': forward.id + 7,
        }, status_code=422)
        forwards = self.db.query(models.ForwardAddress)
        self.assertEquals(forwards.count(), 0)

        # do everything right and look if it get's added to Confirm
        self.api.post("/forwardaddresses", data={
            'email': email,
            'forward_id': forward.id,
        }, status_code=202)
        assignments = self.db.query(models.ForwardAddress)
        self.assertEquals(assignments.count(), 1)
        self.assertEquals(assignments.first()._confirmed, False)

        token = assignments.first()._token
        self.api.post("/confirmations", data={
            'token': token
        }, status_code=201).json
        self.assertEquals(assignments.first()._confirmed, True)

        # try to delete it again
        assignment = self.db.query(models.ForwardAddress).first()
        self.api.delete("/forwardaddresses/%i" % assignment.id,
                        headers={'If-Match': assignment._etag,
                                 'Token': token},
                        status_code=204)
        self.assert_count(models.ForwardAddress, 0)


class ForwardAuthTest(util.WebTest):

    def test_forward_addresses_permissions_GET(self):
        """ Test GET permissions for ForwardAddress objects """
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id, is_public=True)
        self.new_forward_address(forward_id=forward.id,
                                 email=email)

        self.api.get("/forwardaddresses", token=admin_session.token,
                     status_code=200)

        self.api.get("/forwardaddresses",
                     token=list_owner_session.token,
                     status_code=200).json

        # forwardaddresses should just be visible for admin and owner
        response = self.api.get("/forwardaddresses",
                                token=registered_session.token,
                                status_code=200).json
        self.assertEquals(len(response['_items']), 0)

        self.api.get("/forwardaddresses", status_code=401)

    def test_forward_addresses_permissions_POST(self):
        """ Test POST permissions for ForwardAddress objects """
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id, is_public=True)

        data = {
            "email": email,
            "forward_id": forward.id
        }

        self.api.post("/forwardaddresses", data=data, status_code=202)

        self.api.post("/forwardaddresses", data=data,
                      token=registered_session.token,
                      status_code=202)

        self.api.post("/forwardaddresses", data=data,
                      token=entry_user_session.token,
                      status_code=202)

        self.api.post("/forwardaddresses", data=data,
                      token=admin_session.token,
                      status_code=202).json

        self.api.post("/forwardaddresses", data=data,
                      token=list_owner_session.token,
                      status_code=202).json

    def test_forward_addresses_permissions_PATCH(self):
        """ Test PATCH permissions for ForwardAddress objects """

        # PATCH is not allowed for /forwardaddresses nor items
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id, is_public=True)
        forward2 = self.new_forward(owner_id=list_owner.id, is_public=True)
        forward_address = self.new_forward_address(forward_id=forward.id,
                                                   email=email)

        # Try changing the forward
        data = {
            "forward_id": forward2.id
        }

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        forward3 = self.new_forward(owner_id=0, is_public=True)

        data = {
            "forward_id": forward3.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        data = {
            "forward_id": forward.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        data = {
            "forward_id": forward2.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=admin_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        forward_address.forward_id = forward.id

        data = {
            "email": "change@amiv.io"
        }

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        forward_address.user_id = entry_user.id

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

    def test_forward_addresses_permissions_PUT(self):
        """ Test PUT permissions for ForwardAddress objects """

        # PUT is not supported for forwardaddresses
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)
        entry_user = self.new_user()
        entry_user_session = self.new_session(user_id=entry_user.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id, is_public=True)
        forward2 = self.new_forward(owner_id=list_owner.id, is_public=True)
        forward_address = self.new_forward_address(forward_id=forward.id,
                                                   email=email)

        # Try changing the forward
        data = {
            "user_id": entry_user.id,
            "forward_id": forward2.id
        }

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        forward3 = self.new_forward(owner_id=0, is_public=True)

        data = {
            "user_id": entry_user.id,
            "forward_id": forward3.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        data = {
            "user_id": entry_user.id,
            "forward_id": forward.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        data = {
            "email": email,
            "forward_id": forward2.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=admin_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        data = {
            "email": email,
            "forward_id": forward2.id
        }

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=registered_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=list_owner_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=entry_user_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

    def test_forward_addresses_permissions_DELETE(self):
        """ Test DELETE permissions for ForwardAddress objects """
        admin = self.new_user()
        email = u"test-mail@amiv.ethz.ch"
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_session = self.new_session(user_id=admin.id)

        list_owner = self.new_user()
        list_owner_session = self.new_session(user_id=list_owner.id)

        registered = self.new_user()
        registered_session = self.new_session(user_id=registered.id)

        forward = self.new_forward(owner_id=list_owner.id, is_public=True)
        forward_address = self.new_forward_address(forward_id=forward.id,
                                                   email=email)

        # try to delete without token - 403
        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        headers={'If-Match': forward_address._etag},
                        status_code=403)

        # try to delete, but you are not allowed without confirmation-token
        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=registered_session.token,
                        headers={'If-Match': forward_address._etag},
                        status_code=403)

        # delete as list_owner is allowed
        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=list_owner_session.token,
                        headers={'If-Match': forward_address._etag},
                        status_code=204)

        # delete with the token send by email is also allowed
        forward_address = self.new_forward_address(forward_id=forward.id,
                                                   email=email)
        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        headers={'If-Match': forward_address._etag,
                                 'Token': forward_address._token},
                        status_code=204)

        # delete as an admin works always
        forward_address = self.new_forward_address(email=email,
                                                   forward_id=forward.id)

        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=admin_session.token,
                        headers={'If-Match': forward_address._etag},
                        status_code=204)

    def test_role_validation(self):
        """Test /forwardusers for registered user in different roles"""
        user = self.new_user()
        user_token = self.new_session(user_id=user.id).token
        admin = self.new_user()
        self.new_permission(user_id=admin.id, role='vorstand')
        admin_token = self.new_session(user_id=admin.id).token
        peon = self.new_user()
        peon_token = self.new_session(user_id=peon.id).token
        owner = self.new_user()
        owner_token = self.new_session(user_id=owner.id).token

        forward = self.new_forward(is_public=True, owner_id=owner.id)

        # i can post to forwardusers for me
        data = {
            'user_id': user.id,
            'forward_id': forward.id
        }
        self.api.post("/forwardusers", data=data, token=user_token,
                      status_code=201)

        # another user can not signup me
        self.api.post("/forwardusers", data=data, token=peon_token,
                      status_code=403)

        # owner can signup me
        forward = self.new_forward(is_public=True, owner_id=owner.id)
        data.update(forward_id=forward.id)
        self.api.post("/forwardusers", data=data, token=owner_token,
                      status_code=201)

        # admin can signup me
        forward = self.new_forward(is_public=True, owner_id=owner.id)
        data.update(forward_id=forward.id)
        self.api.post("/forwardusers", data=data, token=admin_token,
                      status_code=201)
