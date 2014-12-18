from amivapi.tests import util


class SessionResourceTest(util.WebTest):

    def test_create_session(self):
        """ Tests to obtain a login token """
        password = u"some-really-secure-password"
        user = self.new_user(password=password)

        self.api.post("/sessions", data={
            'username': user.username,
            'password': password,
        }, status_code=201)
