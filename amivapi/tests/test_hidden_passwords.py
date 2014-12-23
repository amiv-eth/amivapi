from amivapi.tests import util


class TestHiddenPasswords(util.WebTestNoAuth):

    def test_passwords_hidden(self):
        user = self.new_user()

        response = self.api.get("/users/%i" % user.id,
                                query_string='projection:{"password":1}',
                                status_code=200)

        self.assertTrue('password' not in response.json)
