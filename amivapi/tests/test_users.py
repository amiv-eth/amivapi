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

        api_user = (u for u in users.json['_items'] if u['username']
                    == user.username).next()
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
            'username': "johndoe",
            'membership': "none",
        }
        for key in ["firstname", "lastname", "username", "email", "gender",
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

        retrived_user = (u for u in users.json['_items'] if u['id']
                         == userid).next()
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
            'username': "johndoe",
            'membership': "none",
        }
        self.api.post("/users", data=data, status_code=422)

        data['email'] = 'test@example.com'
        self.api.post("/users", data=data, status_code=201)
