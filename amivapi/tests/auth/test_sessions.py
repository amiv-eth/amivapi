# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for session."""

from bson import ObjectId
from passlib.context import CryptContext
from passlib.hash import pbkdf2_sha256

from amivapi.auth.sessions import verify_password
from amivapi.tests.utils import WebTest


class AuthentificationTest(WebTest):
    """Various tests for aquiring a session."""

    def test_create_session(self):
        """Test to obtain a login token."""
        password = u"some-really-secure-password"
        nethz = u"somenethz"

        user = self.new_object('users', nethz=nethz, password=password,
                               membership="regular")

        # Login with mail
        response = self.api.post("/sessions",
                                 data={'username': user['email'],
                                       'password': password},
                                 status_code=201).json

        self.assertEqual(response['user'], str(user['_id']))

        # Login with nethz
        r = self.api.post("/sessions", data={
            'username': user['nethz'],
            'password': password,
        }, status_code=201).json

        self.assertEqual(r['user'], str(user['_id']))

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

        self.new_object('users', nethz=nethz, password=password,
                        membership='none')

        # Expect 401 - unauthorized
        self.api.post("/sessions", data={
            'username': nethz,
            'password': password,
        }, status_code=201)

    def test_get_session(self):
        """Assert a user can see his sessions, but not others sessions."""
        user = self.new_object('users', password=u"something")
        session_1 = self.new_object('sessions', username=str(user['_id']),
                                    password=u"something")
        session_2 = self.new_object('sessions', username=str(user['_id']),
                                    password=u"something")

        other_user = self.new_object('users', password=u"something_else")
        other_session = self.new_object('sessions',
                                        username=str(other_user['_id']),
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

        ids = [item['_id'] for item in all_sessions.json['_items']]

        self.assertItemsEqual(ids,
                              [str(session_1['_id']), str(session_2['_id'])])
        self.assertNotIn(other_session['_id'],
                         ids)

    def test_no_public_get(self):
        """Test that there is no public reading of sessions."""
        # Create a sess
        user = self.new_object('users', password=u"something")
        session = self.new_object('sessions',
                                  username=str(user['_id']),
                                  password=u"something")

        self.api.get("/sessions", status_code=401)
        self.api.get("/sessions/%s" % session['_id'], status_code=401)

    def test_wrong_password(self):
        """Test to login with a wrong password."""
        user = self.new_object('users', password=u"something")

        self.api.post("/sessions", data={
            'username': user['email'],
            'password': u"something-else",
        }, status_code=401)

    def test_delete_session(self):
        """Test to logout."""
        password = u"awesome-password"
        user = self.new_object('users', password=password)

        session = self.new_object('sessions', username=str(user['_id']),
                                  password=password)
        token = session['token']

        self.api.delete("/sessions/%s" % session['_id'], token=token,
                        headers={'If-Match': session['_etag']}, status_code=204)

        # Check if still logged in
        self.api.get("/sessions", token=token, status_code=401)

    def test_bad_data(self):
        """Make extra sure data has to be correct to get a session."""
        password = u"some-really-secure-password"
        user = self.new_object('users', nethz=u"abc",
                               email="user@amiv",
                               password=password)
        user_id = str(user['_id'])

        bad_data = [
            {'username': user_id},
            {'password': password},
            {'username': None,
             'password': password},
            {'username': '',
             'password': password},
            {'username': user_id,
             'password': None},
            {'username': "not_user@amiv"}
        ]

        for data in bad_data:
            self.api.post("/sessions",
                          data=data,
                          status_code=422)

    def test_invalid_token(self):
        """Try to do a request using invalid token."""
        self.api.get("/users", token=u"There is no token!", status_code=401)


class PasswordVerificationTest(WebTest):
    """Test if password verfication and rehashing works."""

    def test_verify_hash(self):
        """Test verify hash.

        Also needs app context to access config.
        """
        with self.app.app_context():
            hashed = self.app.config['PASSWORD_CONTEXT'].encrypt(
                "some_pw")

            # Correct password
            self.assertTrue(
                verify_password({'password': hashed}, "some_pw")
            )

            # Wrong password
            self.assertFalse(
                verify_password({'password': hashed}, "NotThePassword")
            )

    def _get_weak_hash(self, plaintext):
        """Create a weaker CryptContext and hash plaintext.

        (Weaker as in weaker than default context)
        """
        weak_context = CryptContext(
            schemes=["pbkdf2_sha256"],
            pbkdf2_sha256__default_rounds=5,
            pbkdf2_sha256__vary_rounds=0.1,
            pbkdf2_sha256__min_rounds=1,
        )

        return weak_context.encrypt(plaintext)

    def assertRehashed(self, user_id, plaintext, old_hash):
        """Assert that the password was rehased.

        Check
        - that the password in the database is not the old hash
        - that the password in the datbase is a correct hash of the password

        Args:
            user_id (ObjectId): Id of user
            plaintext (str): Password of user as plaintext
            old_hash (str): Old hash of passwor
        """
        user = self.db['users'].find_one({'_id': user_id})

        self.assertNotEqual(user['password'], old_hash)

        self.assertTrue(pbkdf2_sha256.verify(plaintext, user['password']))

    def test_verify_hash_rehashes_weak_password(self):
        """Test that verify_password rehashes password.

        This is supposed to happen if the security of the crypt context
        is increased.

        Needs request context because Eve requires this for "patch_internal"
        which is used to updated the hash.
        """
        with self.app.test_request_context():
            db = self.db['users']
            password = "some_pw"
            weak_hash = self._get_weak_hash(password)

            # Add a user with to db. use password hashed with weak context
            user_id = db.insert({
                'password': weak_hash
            })

            user = db.find_one({'_id': ObjectId(user_id)})

            # Verify password, should be true
            self.assertTrue(verify_password(user, password))

            self.assertRehashed(user_id, password, weak_hash)

    def test_hash_update_on_login(self):
        """Test that passwords are rehashed when needed on login."""
        db = self.db['users']
        password = "some_pw"
        weak_hash = self._get_weak_hash(password)

        # Add a user with to db. use password hashed with weak context
        user_id = db.insert({
            'password': weak_hash
        })

        login_data = {
            'username': str(user_id),
            'password': password
        }

        self.api.post("/sessions", data=login_data, status_code=201)

        # Check database
        self.assertRehashed(user_id, password, weak_hash)
