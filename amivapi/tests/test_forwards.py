from amivapi import models
from amivapi.tests import util


class ForwardTest(util.WebTestNoAuth):

    def test_a_assign_registered(self):
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

    def test_b_assign_unregistered(self):
        email = "test-mail@amiv.ethz.ch"
        forward = self.new_forward(is_public=True)

        # forward to non-email-address
        self.api.post("/forwardaddresses", data={
            'address': 'fakeaddress',
            'forward_id': forward.id,
        }, status_code=422)
        forwards = self.db.query(models.ForwardAddress)
        self.assertEquals(forwards.count(), 0)

        # forwards to not existing forward
        self.api.post("/forwardaddresses", data={
            'address': email,
            'forward_id': forward.id + 7,
        }, status_code=422)
        forwards = self.db.query(models.ForwardAddress)
        self.assertEquals(forwards.count(), 0)

        # do everything right and look if it get's added to Confirm
        self.api.post("/forwardaddresses", data={
            'address': email,
            'forward_id': forward.id,
        }, status_code=201)
        forwards = self.db.query(models.ForwardAddress)
        self.assertEquals(forwards.count(), 1)
