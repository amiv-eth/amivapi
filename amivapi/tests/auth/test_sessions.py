# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for session."""

from amivapi.tests.utils import WebTest


class AuthentificationTest(WebTest):
    """Various tests for aquiring a session."""

    def test_create_session(self):
        """Test to obtain a login token."""
        password = u"some-really-secure-password"
        nethz = u"somenethz"

        user = self.new_user(nethz=nethz, password=password,
                             membership="regular")

        # Login with mail
        response = self.api.post("/sessions",
                                 data={'user': user['email'],
                                       'password': password},
                                 status_code=201).json

        self.assertEqual(response['user_id'], str(user['_id']))

        # Login with nethz
        r = self.api.post("/sessions", data={
            'user': user['nethz'],
            'password': password,
        }, status_code=201).json

        self.assertEqual(r['user_id'], str(user['_id']))

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

    def test_get_session(self):
        """Assert a user can see his sessions, but not others sessions."""
        user = self.new_user(password=u"something")
        session_1 = self.new_session(user=str(user['_id']),
                                     password=u"something")
        session_2 = self.new_session(user=str(user['_id']),
                                     password=u"something")

        other_user = self.new_user(password=u"something_else")
        other_session = self.new_session(user=str(other_user['_id']),
                                         password=u"something_else")

        token = session_1['token']
        self.api.get("/sessions/%s" % session_1['_id'],
                     token=token,
                     status_code=200)
        self.api.get("/sessions/%s" % session_2['_id'],
                     token=token,
                     status_code=200)
        self.api.get("/sessions/%s" % other_session['_id'],
                     token=token,
                     status_code=404)

        all_sessions = self.api.get("sessions", token=token, status_code=200)
        print(all_sessions.json)
        print("DONE")
        ids = [item['_id'] for item in all_sessions.json['_items']]

        self.assertItemsEqual(ids,
                              [str(session_1['_id']), str(session_2['_id'])])
        self.assertNotIn(other_session['_id'],
                         ids)

    def test_no_public_get(self):
        """Test that there is no public reading of sessions."""
        # Create a sess
        user = self.new_user(password=u"something")
        session = self.new_session(user=str(user['_id']),
                                   password=u"something")

        self.api.get("/sessions", status_code=401)
        self.api.get("/sessions/%s" % session['_id'], status_code=401)

    def test_wrong_password(self):
        """Test to login with a wrong password."""
        user = self.new_user(password=u"something")

        self.api.post("/sessions", data={
            'user': user['email'],
            'password': u"something-else",
        }, status_code=401)

    def test_delete_session(self):
        """Test to logout."""
        password = u"awesome-password"
        user = self.new_user(password=password)

        session = self.new_session(user=str(user['_id']), password=password)
        token = session['token']

        self.api.delete("/sessions/%s" % session['_id'], token=token,
                        headers={'If-Match': session['_etag']}, status_code=204)

        # Check if still logged in
        self.api.get("/sessions", token=token, status_code=401)

    def test_bad_data(self):
        """Make extra sure data has to be correct to get a session."""
        password = u"some-really-secure-password"
        user = self.new_user(nethz=u"abc",
                             email="user@amiv",
                             password=password)
        user_id = str(user['_id'])

        bad_data = [
            {'user': user_id},
            {'password': password},
            {'user': None,
             'password': password},
            {'user': '',
             'password': password},
            {'user': user_id,
             'password': None},
            {'user': "not_user@amiv"}
        ]

        for data in bad_data:
            self.api.post("/sessions",
                          data=data,
                          status_code=422)

    def test_invalid_token(self):
        """Try to do a request using invalid token."""
        self.api.get("/users", token=u"There is no token!", status_code=401)

    def test_root(self):
        """Test if nethz "root" can be used to log in as root user."""
        # Per default the password is "root"
        r = self.api.post("/sessions", data={
            'user': 'root',
            'password': 'root',
        }, status_code=201)

        self.assertTrue(r.json['user_id'] == 24 * "0")  # logged in as root?
