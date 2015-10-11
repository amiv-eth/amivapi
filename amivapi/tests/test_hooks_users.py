# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class UserHooksTest(util.WebTest):
    def test_password_change(self):
        """ Test if a user can change his password """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        # Nobody can enter this password in his browser,
        # it must be very secure!
        new_pw = u"my_new_pw_9123580:öpäß'+ `&%$§\"!)(\\\xff\x10\xa0"

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"password": new_pw},
                       status_code=200)

        data = {
            "email": user.email,
            "password": new_pw
        }
        self.api.post("/sessions", data=data, status_code=201)

    def test_firstname_change(self):
        """ Test if a user can change his firstname """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"firstname": "new_name"},
                       status_code=403)

    def test_lastname_change(self):
        """ Test if a user can change his lastname """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"lastname": "new_name"},
                       status_code=403)

    def test_birthday_change(self):
        """ Test if a user can change his birthday """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"birthday": "1990-01-01Z"},
                       status_code=403)

    def test_legi_change(self):
        """ Test if a user can change his legi number """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"legi": "10000000"},
                       status_code=403)

    def test_rfid_change(self):
        """ Test if a user can change his rfid number """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"rfid": "100000"},
                       status_code=200)

    def test_nethz_change(self):
        """ Test if a user can change his nethz """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"nethz": "coolkid"},
                       status_code=403)

    def test_department_change(self):
        """ Test if a user can change his department """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"department": "infk"},
                       status_code=403)

    def test_phone_change(self):
        """ Test if a user can change his phone """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"phone": "177"},
                       status_code=403)

    def test_ldap_address_change(self):
        """ Test if a user can change his ldap address """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"ldapAddress": "Weg 1"},
                       status_code=403)

    def test_gender_change(self):
        """ Test if a user can change his gender """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"gender": "male"},
                       status_code=403)

    def test_email_change(self):
        """ Test if a user can change his email """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"email": "no@emaxpsd.com"},
                       status_code=200)

    def test_membership_change(self):
        """ Test if a user can change his email """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"membership": "none"},
                       status_code=403)
