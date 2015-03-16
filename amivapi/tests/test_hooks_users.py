# -*- coding: utf-8 -*-
#
# AMIVAPI test_hooks_users.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from amivapi.tests import util


class UserHooksTest(util.WebTest):

    def test_username_change(self):
        """ Test if a user can change his username """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"username": "new_name"},
                       status_code=403)

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
            "username": user.username,
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
