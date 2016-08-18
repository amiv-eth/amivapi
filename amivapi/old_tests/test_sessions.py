# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class AuthentificationTest(util.WebTest):
    """Various tests for aquiring a session."""

    def test_create_session(self):
        """Test to obtain a login token."""
        password = u"some-really-secure-password"
        nethz = u"somenethz"

        user = self.new_user(nethz=nethz, password=password,
                             membership="regular")

        # Login with mail
        r = self.api.post("/sessions", data={
            'user': user.email,
            'password': password,
        }, status_code=201).json

        self.assertEqual(r['user_id'], user.id)

        # Login with nethz
        r = self.api.post("/sessions", data={
            'user': user.nethz,
            'password': password,
        }, status_code=201).json

        self.assertEqual(r['user_id'], user.id)

    def test_no_member(self):
        """Test that non members can log in too.

        Other ETH students which aren't members of our organisation sometimes
        visit the same lectures as our students and we want to share the
        relevant documents with them. Therefore they also need to be able to
        log in.

        Everyone that can be authenticated by ldap will be in the database.
        """
        password = u"some-really-secure-password"
        nethz = u"somenethz"

        self.new_user(nethz=nethz, password=password,
                      membership=None)

        # Expect 401 - unauthorized
        self.api.post("/sessions", data={
            'user': nethz,
            'password': password,
        }, status_code=201)

    def test_bad_nethz(self):
        """Test bad username.

        May not be None or empty
        """
        password = u"some-really-secure-password"
        self.new_user(nethz=u"abc", password=password)

        self.api.post("/sessions", data={
            'user': None,
            'password': password,
        }, status_code=422)

        self.api.post("/sessions", data={
            'user': '',
            'password': password,
        }, status_code=422)

    def test_bad_pass(self):
        """Test if empty password is correctly rejected."""
        user = u"abc"
        password = u"some-really-secure-password"
        self.new_user(nethz=user, password=password)

        self.api.post("/sessions", data={
            'user': user,
            'password': None,
        }, status_code=422)

    def test_wrong_password(self):
        """Test to login with a wrong password."""
        user = self.new_user(password=u"something")

        self.api.post("/sessions", data={
            'user': user.email,
            'password': u"something-else",
        }, status_code=401)

    def test_delete_session(self):
        """Test to logout."""
        password = u"awesome-password"
        user = self.new_user(password=password)

        session = self.new_session(user_id=user.id)

        # Check if the user is logged in
        self.api.get("/sessions", token=session.token, status_code=200)

        self.api.delete("/sessions/%i" % session.id, token=session.token,
                        headers={'If-Match': session._etag}, status_code=204)

        # Check if still logged in
        self.api.get("/sessions", token=session.token, status_code=401)

    def test_invalid_mail(self):
        """Try to login with an unknown username."""
        self.new_user(email=u"user1@amiv", password=u"user1")

        self.api.post("/sessions", data={'user': u"user2@amiv",
                                         'password': u"user1"}, status_code=401)

    def test_no_email(self):
        """Try to login without username."""
        self.new_user(email="user1@amiv")

        self.api.post("/sessions", data={'password': u'mypw'}, status_code=422)

    def test_no_password(self):
        """Try to login without password."""
        self.new_user(email=u"user1@amiv")

        self.api.post("/sessions", data={'user': u'user1@amiv'},
                      status_code=422)

    def test_invalid_token(self):
        """Try to do a request using invalid token."""
        self.new_session()

        self.api.get("/users", token=u"xxx", status_code=401)

    def test_root(self):
        """Test if nethz "root" can be used to log in as root user."""
        # Per default the password is "root"
        r = self.api.post("/sessions", data={
            'user': 'root',
            'password': 'root',
        }, status_code=201)

        self.assertTrue(r.json['user_id'] == 0)  # logged in as root?
