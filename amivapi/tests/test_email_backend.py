# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from os.path import exists

from amivapi.tests import util


class ForwardBackendTest(util.WebTestNoAuth):

    def _get_path(self, group_address):
        return "%s/.forward+%s" % (self.app.config['FORWARD_DIR'],
                                   group_address)

    def _is_content(self, group_address, content_lines):
        """ Take a list of lines and check if a file contains exactly those"""
        # Get File content
        with open(self._get_path(group_address)) as f:
            file_lines = f.read().splitlines()

        return (set(file_lines) == set(content_lines))

    def test_file_creation(self):
        """ Test that new email addresses are added and removed correctly from
        all associated forwards

        In this tests it is important to use the api methods instead of the
        self.new_xxx shortcut since the latter aproach doesnt trigger the hooks
        which manage the forwards
        """
        group = self.new_group()
        address_1 = self.new_group_address(group_id=group.id)
        address_2 = self.new_group_address(group_id=group.id)

        # Test adding a user
        user = self.new_user(email=u"test@no.no")
        guser = self.api.post("/groupmembers", data=dict(
            user_id=user.id, group_id=group.id)).json

        # Verify address is added to both forwards
        mail_list = [user.email]
        self.assertTrue(self._is_content(address_1.email, mail_list))
        self.assertTrue(self._is_content(address_2.email, mail_list))

        # Test adding a forward
        forward = self.api.post("/groupforwards", data={
            'email': u"verteiler@no.no",
            'group_id': group.id
        }).json

        mail_list.append(forward['email'])
        self.assertTrue(self._is_content(address_1.email, mail_list))
        self.assertTrue(self._is_content(address_2.email, mail_list))

        # Delete membership
        self.api.delete("/groupmembers/%i" % guser['id'],
                        headers={"If-Match": guser['_etag']},
                        status_code=204)

        mail_list.remove(user.email)
        self.assertTrue(self._is_content(address_1.email, mail_list))
        self.assertTrue(self._is_content(address_2.email, mail_list))

        # Delete membership
        self.api.delete("/groupforwards/%i" % forward['id'],
                        headers={"If-Match": forward['_etag']},
                        status_code=204)

        mail_list.remove(forward['email'])
        self.assertTrue(self._is_content(address_1.email, mail_list))
        self.assertTrue(self._is_content(address_2.email, mail_list))

        for forward in [address_1, address_2]:
            self.api.delete('/groupaddresses/%s' % forward.id,
                            headers={"If-Match": forward._etag})

            path = self._get_path(forward.email)
            self.assertFalse(exists(path))

    def test_unique_combination(self):
        """ Test that u can add two different users, but not the same user
        twice. But the same you to a different group.

        Similarly forwards not possible twice per group

        Addresses have to be completely unique
        """
        group_1 = self.new_group()
        group_2 = self.new_group()

        # Users
        user_1 = self.new_user()
        user_2 = self.new_user()

        self.api.post("/groupmembers",
                      data=dict(user_id=user_1.id, group_id=group_1.id),
                      status_code=201)
        # Same user, other group
        self.api.post("/groupmembers",
                      data=dict(user_id=user_1.id, group_id=group_2.id),
                      status_code=201)
        # same user, same group -> bad
        self.api.post("/groupmembers",
                      data=dict(user_id=user_1.id, group_id=group_1.id),
                      status_code=422)
        # other user, same group
        self.api.post("/groupmembers",
                      data=dict(user_id=user_2.id, group_id=group_1.id),
                      status_code=201)

        # Forwards
        forward_1 = "lala@lu.lo"
        forward_2 = "lolo@la.li"

        self.api.post("/groupforwards",
                      data=dict(email=forward_1, group_id=group_1.id),
                      status_code=201)
        # Same forward, other group
        self.api.post("/groupforwards",
                      data=dict(email=forward_1, group_id=group_2.id),
                      status_code=201)
        # same forward, same group -> bad
        self.api.post("/groupforwards",
                      data=dict(email=forward_1, group_id=group_1.id),
                      status_code=422)
        # other forward, same group
        self.api.post("/groupforwards",
                      data=dict(email=forward_2, group_id=group_1.id),
                      status_code=201)

        # Addresses
        address_1 = "lala@lu.lo"
        address_2 = "lolo@la.li"

        self.api.post("/groupaddresses",
                      data=dict(email=address_1, group_id=group_1.id),
                      status_code=201)
        # Same address, other group -> bad
        self.api.post("/groupaddresses",
                      data=dict(email=address_1, group_id=group_2.id),
                      status_code=422)
        # same address, same group -> bad
        self.api.post("/groupaddresses",
                      data=dict(email=address_1, group_id=group_1.id),
                      status_code=422)
        # other address, same group -> ok
        self.api.post("/groupaddresses",
                      data=dict(email=address_2, group_id=group_1.id),
                      status_code=201)
