# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from os.path import exists

from amivapi.tests import util


class ForwardBackendTest(util.WebTestNoAuth):

    def test_forward_creation(self):
        session = self.new_session()

        group = self.new_group()
        forward_address = self.new_forward_address(group_id=group.id)
        forward_address2 = self.new_forward_address(group_id=group.id)

        # Test adding a user

        user = self.new_user(email=u"test@no.no")

        guser = self.api.post("/groupusermembers", data={
            'user_id': user.id,
            'group_id': group.id,
        }, token=session.token, status_code=201).json

        for forw in [forward_address, forward_address2]:
            path = "%s/.forward+%s" % (self.app.config['FORWARD_DIR'],
                                       forw.address)
            self.assertTrue(util.is_file_content(path, "test@no.no\n"))

        # Test adding an address directly

        self.api.post("/groupaddressmembers", data={
            'email': u"looser92@gmx.com",
            'group_id': group.id,
        }, token=session.token, status_code=202).json

        for forw in [forward_address, forward_address2]:
            path = "%s/.forward+%s" % (self.app.config['FORWARD_DIR'],
                                       forw.address)
            self.assertTrue(util.is_file_content(
                path, "test@no.no\nlooser92@gmx.com\n"))

        # Test deleting an entry

        self.api.delete("/groupusermembers/%i" % guser['id'],
                        token=session.token,
                        headers={"If-Match": guser['_etag']},
                        status_code=204)

        for forw in [forward_address, forward_address2]:
            path = "%s/.forward+%s" % (self.app.config['FORWARD_DIR'],
                                       forw.address)
            self.assertTrue(util.is_file_content(path, "looser92@gmx.com\n"))

        # Test deleting the address

        self.api.delete("/forwardaddresses/%i" % forward_address.id,
                        token=session.token,
                        headers={"If-Match": forward_address._etag},
                        status_code=204)

        path = "%s/.forward+%s" % (self.app.config['FORWARD_DIR'],
                                   forward_address.address)
        self.assertTrue(exists(path) is False)
