from amivapi.tests import util


class SessionResourceTest(util.WebTest):

    def test_create_session(self):
        """ Test to obtain a login token """
        password = u"some-really-secure-password"
        user = self.new_user(password=password)

        self.api.post("/sessions", data={
            'username': user.username,
            'password': password,
        }, status_code=201)

    def test_delete_session(self):
        """ Test to logout """
        password = u"awesome-password"
        user = self.new_user(password=password)

        session = self.new_session(user_id=user.id)

        """ Check if the user is logged in """
        self.api.get("/sessions", token=session.token, status_code=200)

        self.api.delete("/sessions/%i" % session.id, token=session.token,
                        headers={'If-Match': session._etag}, status_code=200)

        """ Check if still logged in """
        self.api.get("/sessions", session.token, status_code=401)
