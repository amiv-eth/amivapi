# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from os.path import exists

from amivapi.tests import util


class ForwardBackendTest(util.WebTestNoAuth):

    def _get_path(self, forward_address):
        return "%s/.forward+%s" % (self.app.config['FORWARD_DIR'],
                                   forward_address)

    def _assert_content(self, forward_address, content):
        path = self._get_path(forward_address)
        self.assertTrue(util.is_file_content(path, content))

    def test_forward_creation(self):
        """ Test that new email addresses are added and removed correctly from
        all associated forwards

        In this tests it is important to use the api methods instead of the
        self.new_xxx shortcut since the latter aproach doesnt trigger the hooks
        which manage the forwards
        """
        session = self.new_session()

        group = self.new_group()
        forward_1 = self.new_group_address(group_id=group.id)
        forward_2 = self.new_group_address(group_id=group.id)

        # Test adding a user
        user_1 = self.new_user(email=u"test@no.no")
        guser_1 = self.api.post("/groupmembers", data=dict(
            user_id=user_1.id, group_id=group.id)).json

        # Verify addresses are added to both forwards
        for forward in [forward_1.email, forward_2.email]:
            self._assert_content(forward, "%s\n" % user_1.email)

        # Add another
        user_2 = self.new_user(email=u"zzz@yes.maybe")
        guser_2 = self.api.post("/groupmembers", data=dict(
            user_id=user_2.id, group_id=group.id)).json

        # Verify both addresses are in both forwards
        content = "%s\n%s\n" % (user_1.email, user_2.email)
        for forward in [forward_1.email, forward_2.email]:
            self._assert_content(forward, content)

        # Delete one entry
        self.api.delete("/groupmembers/%i" % guser_1['id'],
                        token=session.token,
                        headers={"If-Match": guser_1['_etag']},
                        status_code=204)

        for forward in [forward_1.email, forward_2.email]:
            self._assert_content(forward, "%s\n" % user_2.email)

        # Delete second entry, files should be gone then
        self.api.delete("/groupmembers/%i" % guser_2['id'],
                        token=session.token,
                        headers={"If-Match": guser_2['_etag']},
                        status_code=204)

        # Remove groupaddresses, lists should be gone then
        for forward in [forward_1, forward_2]:
            self.api.delete('/groupaddresses/%s' % forward.id,
                            headers={"If-Match": forward._etag})

            path = self._get_path(forward.email)
            self.assertFalse(exists(path))
