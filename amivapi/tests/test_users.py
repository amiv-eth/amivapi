# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import datetime as dt

from amivapi import models, settings
from amivapi.tests import util


class UserResourceTest(util.WebTestNoAuth):

    def test_users_collection(self):
        # Only root and anonymous to start with
        no_users = self.api.get("/users", status_code=200)
        self.assertEquals(len(no_users.json['_items']), 2)

        user = self.new_user()
        users = self.api.get("/users", status_code=200)
        self.assertEquals(len(users.json['_items']), 3)

        api_user = next(u for u in users.json['_items'] if u['email']
                        == user.email)

        for col in models.User.__table__.c:
            if col.key == 'password':
                continue
            self.assertIn(col.key, api_user)

            model_value = getattr(user, col.key)
            if isinstance(model_value, dt.datetime):
                model_value = model_value.strftime(settings.DATE_FORMAT)

            self.assertEquals(model_value, api_user[col.key])

        single_user = self.api.get("/users/%i" % api_user['id'],
                                   status_code=200)
        self.assertEquals(api_user.keys(), single_user.json.keys())
        for key, value in api_user.items():
            if key == "_links":
                # By definition, the links are quite different for collections
                # and items
                continue
            self.assertEquals(value, single_user.json[key])

    def test_create_user(self):
        # POSTing to /users with missing required fields yields an error, and
        # no document is created
        data = {
            'firstname': "John",
            'lastname': "Doe",
            'email': "john-doe@example.net",
            'gender': "male",
            'membership': "none",
        }
        for key in ["firstname", "lastname", "email", "gender",
                    "membership"]:
            crippled_data = data.copy()
            crippled_data.pop(key)
            self.api.post("/users",
                          data=crippled_data,
                          status_code=422)

            user_count = self.db.query(models.User).count()
            self.assertEquals(user_count, 2)

        user = self.api.post("/users", data=data, status_code=201)
        userid = user.json['id']

        users = self.api.get("/users", status_code=200)
        self.assertEquals(len(users.json['_items']), 3)

        retrived_user = next(u for u in users.json['_items'] if u['id']
                             == userid)
        for key in data:
            self.assertEquals(retrived_user[key], data[key])

        user_count = self.db.query(models.User).count()
        self.assertEquals(user_count, 3)

    def test_user_invalid_mail(self):
        data = {
            'firstname': "John",
            'lastname': "Doe",
            'email': "youdontgetmail",
            'gender': "male",
            'membership': "none",
        }
        self.api.post("/users", data=data, status_code=422)

        data['email'] = 'test@example.com'
        self.api.post("/users", data=data, status_code=201)

    def test_password_change(self):
        """ Test if a member can change his password """
        user = self.new_user(membership="regular")
        session = self.new_session(user_id=user.id)

        # Nobody can enter this password in his browser,
        # it must be very secure!
        new_pw = u"my_new_pw_9123580:öpäß'+ `&%$§\"!)(\\\xff\x10\xa0"

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"password": new_pw},
                       status_code=200)

        data = {
            "user": user.email,
            "password": new_pw
        }
        self.api.post("/sessions", data=data, status_code=201)

    def test_rfid_change(self):
        """ Test if a user can change his rfid number """

        user = self.new_user()
        session = self.new_session(user_id=user.id)

        self.api.patch("/users/%i" % user.id, token=session.token,
                       headers={"If-Match": user._etag},
                       data={"rfid": "100000"},
                       status_code=200)


class UserItemPermissions(util.WebTest):
    def test_not_patchable_unless_admin(self):
        """ Assert that a user can not change the following values, but an
        an admin can
        """
        user = self.new_user(gender='female', department='itet')
        user_token = self.new_session(user_id=user.id).token
        user_etag = user._etag  # This way we can overwrite it later easily
        # admin
        admin = self.new_user()
        admin_token = self.new_session(user_id=admin.id).token
        admin_group = self.new_group(
            allow_self_enrollment=False,
            permissions={
                'users': {'PATCH': True}
            })
        self.new_group_member(user_id=admin.id,
                              group_id=admin_group.id)

        bad_changes = [
            {"firstname": "new_name"},
            {"lastname": "new_name"},
            {"legi": "10000000"},
            {"nethz": "coolkid"},
            {"department": "mavt"},
            {"phone": "177"},
            {"gender": "male"},
            {"membership": "none"},
        ]

        def try_patching(data, token, etag, status_code):
            return self.api.patch("/users/%i" % user.id, token=token,
                                  headers={"If-Match": etag},
                                  data=data,
                                  status_code=status_code).json

        # The user can change none of those fields
        for bad_data in bad_changes:
            try_patching(bad_data, user_token, user_etag, 422)

        # The admin can
        for data in bad_changes:
            user_etag = try_patching(
                data, admin_token, user_etag, 200)['_etag']
