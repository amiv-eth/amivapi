import datetime as dt

from amivapi import models, settings
from amivapi.tests import util


class UserResourceTest(util.WebTest):

    def test_users_collection(self):
        no_users = self.api.get("/users", status_code=200)
        self.assertEquals(len(no_users.json['_items']), 0)

        user = self.new_user()
        users = self.api.get("/users", status_code=200)
        self.assertEquals(len(users.json['_items']), 1)

        api_user = users.json['_items'][0]
        for col in models.User.__table__.c:
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
        for key in ["firstname", "lastname", "username", "email", "gender"]:
            self.api.post("/users",
                          data={key: "not_enough"},
                          status_code=422)

            user_count = self.db.query(models.User).count()
            self.assertEquals(user_count, 0)

        user = self.api.post("/users", data={
            'firstname': "John",
            'lastname': "Doe",
            'email': "john-doe@example.net",
            'gender': "male",
            'username': "johndoe",
        }, status_code=201)
        userid = user.json['id']

        users = self.api.get("/users", status_code=200)
        self.assertEquals(len(users.json['_items']), 1)
        self.assertEquals(users.json['_items'][0]['id'], userid)

        user_count = self.db.query(models.User).count()
        self.assertEquals(user_count, 1)
