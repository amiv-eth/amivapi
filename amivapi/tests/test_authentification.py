# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class AuthentificationTest(util.WebTest):

    def test_invalid_username(self):
        """ Try to login with an unknown username """
        self.new_user(username=u"user1", password=u"user1")

        self.api.post("/sessions", data={'username': u"user1\0",
                                         'password': u"user1"}, status_code=401)

    def test_no_usernames(self):
        """ Try to login without username """
        self.new_user(username="user1")

        self.api.post("/sessions", data={'password': u'mypw'}, status_code=422)

    def test_no_password(self):
        """ Try to login without password """
        self.new_user(username=u"user1")

        self.api.post("/sessions", data={'username': u'user1'}, status_code=422)

    def test_invalid_token(self):
        """ Try to do a request using invalid token """
        self.new_session()

        self.api.get("/users", token=u"xxx", status_code=401)
