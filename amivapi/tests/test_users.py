# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for user module.

Includes item and field permissions as well as password hashing.
"""


from amivapi.tests import util
from amivapi.users import verify_password

from passlib.context import CryptContext


class UserTest(util.WebTestNoAuth):
    """Basic tests for user resource."""

    def test_methods(self):
        """Test that all basic methods work."""
        post_data = {
            'firstname': 'T',
            'lastname': 'Estuser',
            'gender': 'female',
            'membership': 'regular',
            'email': 'test@user.amiv'
        }

        user = self.api.post("/users", data=post_data, status_code=201).json

        # Try get
        self.api.get("/users", status_code=200)
        self.api.get("/users/%s" % user['_id'], status_code=200)

        # Patch something
        patch_data = {
            'email': 'newemail@shinymail.com'
        }

        # Add etag
        headers = {
            'If-Match': user['_etag']
        }

        user = self.api.patch("/users/%s" % user['_id'],
                              data=patch_data, headers=headers,
                              status_code=200).json

        # Update etag
        headers = {
            'If-Match': user['_etag']
        }

        # Remove
        self.api.delete("/users/%s" % user['_id'], headers=headers,
                        status_code=204)

    def test_nethz_lookup(self):
        """Test that a user can be accessed with nethz name."""
        nethz = "testnethz"

        self.new_user(nethz=nethz)

        self.api.get("/users/%s" % nethz, status_code=200)

    def test_root_and_anonymous(self):
        """Test that root and anonymous user are in the db.

        TODO: Implement.
        """
        pass


class PasswordHashing(util.WebTestNoAuth):
    """Tests password hashing.

    TODO(ALEX): Restructure this, test both the hash hook indepentently and
    if it was integrated correctly.
    """

    def test_hidden_password(self):
        """Assert that password hash can not be retrieved."""
        user_id = self.new_user(password="somepw")['_id']

        # Normal get
        r = self.api.get("/users/%s" % user_id, status_code=200).json

        assert 'password' not in r.keys()

        # Try to force projection
        # This should return a 403 error because we are trying to set a
        # forbidden projection
        self.api.get(u'/users/%s?projection={"password": 1}' % user_id,
                     status_code=403).json

    def _was_hashed(self, plaintext, user_id):
        """Check that saved password exists, is not empty and not plaintext.

        Since there is no way to access the pw from outside this will take
        the user id and fetch the user from the database.

        Args:
            plaintext (str): The password in plaintext.
            user_id (str): The user.

        Returns:
            bool: True if password was not stored and not as plaintext.
                False otherwise.
        """
        user = self.db["users"].find_one(_id=user_id)

        return user['password'] not in [None, "", plaintext]

    def test_hash(self):
        """Assert passwort is hashed when created or updated."""
        password = "supersecret"

        post_data = {
            'firstname': 'T',
            'lastname': 'Estuser',
            'gender': 'female',
            'membership': 'regular',
            'email': 'test@user.amiv',
            'password': password
        }

        user = self.api.post("/users", data=post_data, status_code=201).json

        self.assertTrue(self._was_hashed(password, user['_id']))

        new_password = "evenmoresecret"
        patch_data = {'password': new_password}

        headers = {'If-Match': user['_etag']}
        user = self.api.patch("/users/%s" % user['_id'],
                              headers=headers, data=patch_data,
                              status_code=200).json

        self.assertTrue(self._was_hashed(new_password, user['_id']))

    def test_rehash(self):
        """Assert passwort is rehashed if the cryptcontext is changed."""
        # Modify context (see settings.py for original context)
        self.app.config['PASSWORD_CONTEXT'] = CryptContext(
            schemes=["pbkdf2_sha256"],
            pbkdf2_sha256__default_rounds=10 ** 2,
            pbkdf2_sha256__vary_rounds=0.1,
            pbkdf2_sha256__min_rounds=8 * 10 ** 1,
        )

        # Create user

        password = "supersecret"

        post_data = {
            'firstname': 'T',
            'lastname': 'Estuser',
            'gender': 'female',
            'membership': 'regular',
            'email': 'test@user.amiv',
            'password': password
        }

        user = self.api.post("/users", data=post_data, status_code=201).json

        # Get from db to include password
        db = self.db['users']
        uid = user['_id']

        user = db.find_one(_id=uid)

        # Call verify, nothing changes
        old_pw = user['password']

        # Verify password needs test request context
        with self.app.test_request_context():
            self.assertTrue(verify_password(user, password))

        user = db.find_one(_id=uid)
        self.assertEqual(user['password'], old_pw)

        # Update context
        self.app.config['PASSWORD_CONTEXT'] = CryptContext(
            schemes=["pbkdf2_sha256"],
            pbkdf2_sha256__default_rounds=10 ** 6,
            pbkdf2_sha256__vary_rounds=0.1,
            pbkdf2_sha256__min_rounds=8 * 10 ** 4,
        )

        # Call verify, password should still work
        with self.app.test_request_context():
            self.assertTrue(verify_password(user, password))

        # Assert pw was rehashed
        user = db.find_one(_id=uid)
        self.assertNotEqual(user['password'], old_pw)


class UserFieldPermissions(util.WebTest):
    """Test field permissions.

    Some fields can be changed by the user, some only by admins.
    """

    def test_change_by_user(self):
        """User can change password, email. and rfid."""
        pass

    def test_not_patchable_unless_admin(self):
        """Admin can change everything."""
        return  # TODO: NEEDS GROUPS/Some admin functionality
        user = self.new_user(gender='female', department='itet',
                             nethz='user', password="userpass")
        user_token = self.new_session(
            nethz='user', password="userpass")['token']
        user_etag = user['_etag']  # This way we can overwrite it later easily
        # admin
        admin = self.new_user(nethz='admin', password="adminpass")
        admin_token = self.new_session(
            nethz='admin', password="adminpass")['token']

        admin_group = self.new_group(
            allow_self_enrollment=False,
            permissions={
                'users': {'PATCH': True}
            })
        self.new_group_member(user_id=admin['id'],
                              group_id=admin_group['id'])

        bad_changes = [
            {"firstname": "new_name"},
            {"lastname": "new_name"},
            {"legi": "10000000"},
            {"nethz": "coolkid"},
            {"department": "mavt"},
            {"gender": "male"},
            {"membership": "none"},
        ]

        def try_patching(data, token, etag, status_code):
            return self.api.patch("/users/%i" % user['id'], token=token,
                                  headers={"If-Match": etag},
                                  data=data,
                                  status_code=status_code).json

        # The user can change none of those fields
        for bad_data in bad_changes:
            try_patching(bad_data, user_token, user_etag, 422)

        # The admin can
        for data in bad_changes:
            user_etag = try_patching(
                data, admin_token, user_etag, 200)['_etag']
