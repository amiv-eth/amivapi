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
            'address': 'fakeaddress',
            'forward_id': forward.id,
        }, status_code=422)
        forwards = self.db.query(models._ForwardAddress)
        self.assertEquals(forwards.count(), 0)

        # forwards to not existing forward
        self.api.post("/forwardaddresses", data={
            'address': email,
            'forward_id': forward.id + 7,
        }, status_code=422)
        forwards = self.db.query(models._ForwardAddress)
        self.assertEquals(forwards.count(), 0)

        # do everything right and look if it get's added to Confirm
        self.api.post("/forwardaddresses", data={
            'address': email,
            'forward_id': forward.id,
        }, status_code=202)
        confirms = self.db.query(models.Confirm)
        self.assertEquals(confirms.count(), 1)

        token = confirms.first().token
        self.api.post("/confirmations", data={
            'token': token
        }, status_code=201)
        self.assert_count(models.Confirm, 0)
        self.assert_count(models._ForwardAddress, 1)

        # try to delete it again
        assignment = self.db.query(models._ForwardAddress).first()
        self.api.delete("/forwardaddresses/%i" % assignment.id,
                        headers={'If-Match': assignment._etag},
                        status_code=202)
        self.assert_count(models._ForwardAddress, 1)
        confirms = self.db.query(models.Confirm)
        self.assertEquals(confirms.count(), 1)

        token = confirms.first().token
        self.api.post("/confirmations", data={
            'token': token
        }, status_code=200)
        self.assert_count(models.Confirm, 0)
        self.assert_count(models._ForwardAddress, 0)

    def test_test_internal_resource(self):
        forward = self.new_forward(is_public=True)

        # internal resource should not be accessed
        self.api.get("/_forwardaddresses", status_code=404)
        self.api.post("/_forwardaddresses", status_code=404)

        assignment = self.new_forward_address(forward_id=forward.id)
        self.api.get("/_forwardaddresses/%i" % assignment.id, status_code=404)
        self.api.patch("/_forwardaddresses/%i" % assignment.id,
                       status_code=404)
        self.api.delete("_forwardaddresses/%i" % assignment.id,
                        status_code=404)


class ForwardAuthTest(util.WebTest):

    def test_forward_addresses_permissions_GET(self):
        """ Test GET permissions for _ForwardAddress objects """
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
                                 address=email)

        self.api.get("/forwardaddresses", token=admin_session.token,
                     status_code=200)

        self.api.get("/forwardaddresses",
                     token=list_owner_session.token,
                     status_code=200)

        # forwardaddresses should just be visible for admin and owner
        self.api.get("/forwardaddresses",
                     token=registered_session.token,
                     status_code=401)

        self.api.get("/forwardaddresses", status_code=401)

    def test_forward_addresses_permissions_POST(self):
        """ Test POST permissions for _ForwardAddress objects """
        db = self.app.data.driver.session

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
            "address": email,
            "forward_id": forward.id
        }

        self.api.post("/forwardaddresses", data=data, status_code=202)

        self.api.post("/forwardaddresses", data=data,
                      token=registered_session.token,
                      status_code=202)

        self.api.post("/forwardaddresses", data=data,
                      token=entry_user_session.token,
                      status_code=202)

        new_forward = self.api.post("/forwardaddresses", data=data,
                                    token=admin_session.token,
                                    status_code=201).json

        new_forward = self.api.post("/forwardaddresses", data=data,
                                    token=list_owner_session.token,
                                    status_code=201).json

        db.query(models._ForwardAddress).filter_by(id=new_forward['id']). \
            delete()
        db.commit()

    def test_forward_addresses_permissions_PATCH(self):
        """ Test PATCH permissions for _ForwardAddress objects """

        """ PATCH is not allowed for /forwardaddresses nor items """
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
                                                   address=email)

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
            "address": "change@amiv.io"
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
        """ Test PUT permissions for _ForwardAddress objects """

        """ PUT is not supported for forwardaddresses"""
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
                                                   address=email)

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
            "address": email,
            "forward_id": forward2.id
        }
        self.api.patch("/forwardaddresses/%i" % forward_address.id, data=data,
                       token=admin_session.token,
                       headers={'If-Match': forward_address._etag},
                       status_code=405)

        data = {
            "address": email,
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
        """ Test DELETE permissions for _ForwardAddress objects """
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
                                                   address=email)

        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        headers={'If-Match': forward_address._etag},
                        status_code=202)

        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=registered_session.token,
                        headers={'If-Match': forward_address._etag},
                        status_code=202)

        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=list_owner_session.token,
                        headers={'If-Match': forward_address._etag},
                        status_code=200)

        forward_address = self.new_forward_address(address=email,
                                                   forward_id=forward.id)

        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=admin_session.token,
                        headers={'If-Match': forward_address._etag},
                        status_code=200)
