from amivapi.tests import util
from amivapi import models


class DeletionTests(util.WebTestNoAuth):

    def test_delete_user_to_forwarduser(self):
        user = self.new_user()
        forward = self.new_forward()
        self.new_forward_user(user_id=user.id, forward_id=forward.id)

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': user._etag}, status_code=204)
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 0)
        # We want the forwarduser-entry to be deleted but not the forward
        # itself
        forward_count = self.db.query(models.Forward).count()
        self.assertEquals(forward_count, 1)

    def test_delete_forward_to_forwarduser_forwardaddress(self):
        user = self.new_user()
        forward = self.new_forward()
        self.new_forward_user(user_id=user.id, forward_id=forward.id)
        self.new_forward_address(forward_id=forward.id)

        self.api.delete("/forwards/%i" % forward.id,
                        headers={'If-Match': forward._etag}, status_code=204)
        forward_count = self.db.query(models.Forward).count()
        self.assertEquals(forward_count, 0)
        # forwarduser and forwardaddress entries should now be deleted
        forwarduser_count = self.db.query(models.ForwardUser).count()
        self.assertEquals(forwarduser_count, 0)
        forwardaddress_count = self.db.query(models._ForwardAddress).count()
        self.assertEquals(forwardaddress_count, 0)

    def test_delete_user_to_permission(self):
        user = self.new_user()
        permission = self.new_permission(user_id=user.id, role='vorstand')

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': permission._etag},
                        status_code=204)
        # We have with ids -1 and 0 2 users left after our user got deleted
        self.assert_count(models.User, 2)
        self.assert_count(models.Permission, 0)

    def test_delete_event_to_signup(self):
        event = self.new_event()
        self.new_signup(event_id=event.id)

        self.api.delete("/events/%i" % event.id,
                        headers={'If-Match': event._etag},
                        status_code=204)
        self.assert_count(models.Event, 0)
        self.assert_count(models._EventSignup, 0)

    def test_delete_user_to_signup(self):
        event = self.new_event()
        user = self.new_user()
        self.new_signup(event_id=event.id, user_id=user.id)

        self.api.delete("/users/%i" % user.id,
                        headers={'If-Match': user._etag},
                        status_code=204)
        # We have with ids -1 and 0 2 users left after our user got deleted
        self.assert_count(models.User, 2)
        self.assert_count(models._EventSignup, 0)
        # the Event shold still exist
        self.assert_count(models.Event, 1)
