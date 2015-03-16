# -*- coding: utf-8 -*-
#
# AMIVAPI test_users.py
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
        print api_user
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
