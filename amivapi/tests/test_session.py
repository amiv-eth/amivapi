from amivapi.tests import util
from amivapi.auth import create_new_hash


class SessionResourceTest(util.WebTest):

    def test_create_session(self):
        """ Tests to obtain a login token """
        password = u"some-really-secure-password"
        password_hash = create_new_hash(password)
        user = self.new_user(password=password_hash)

        self.api.post("/sessions", data={
            'username': user.username,
            'password': password,
        }, status_code=201)
