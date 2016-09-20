# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for user module.

Includes item and field permissions as well as password hashing.
"""

from bson import ObjectId

from amivapi.tests import utils
from amivapi.users.security import (
    hash_on_insert, hash_on_update, verify_password)

from passlib.context import CryptContext
from passlib.hash import pbkdf2_sha256


class PasswordHashing(utils.WebTestNoAuth):
    """Tests password hashing.

    TODO(Alex): Test rehash on login as soon as auth works.
    """

    def setUp(self):
        """Extend setup to provide some crypt contexts.

        A "strong" and a "weak" context.

        N.B. The names "strong" and "weak" don't have any meaning about how
        secure they really are.

        An the "real" context taken from app settings.

        Also provide two passwords and the corresponding hashes to test every-
        thing
        """
        # Call normal setUp
        super(PasswordHashing, self).setUp()

        self.strong_context = CryptContext(
            schemes=["pbkdf2_sha256"],
            pbkdf2_sha256__default_rounds=10 ** 4,
            pbkdf2_sha256__vary_rounds=0.1,
            pbkdf2_sha256__min_rounds=8 * 10 ** 3,
        )

        self.weak_context = CryptContext(
            schemes=["pbkdf2_sha256"],
            pbkdf2_sha256__default_rounds=10 ** 2,
            pbkdf2_sha256__vary_rounds=0.1,
            pbkdf2_sha256__min_rounds=8 * 10 ** 1,
        )

        self.real_context = self.app.config['PASSWORD_CONTEXT']

        self.pw_1 = "some_pw"
        self.pw_2 = "other_pw"

    def assertVerify(self, plaintext, hashed_password):
        """Assert the hash matches the password."""
        self.assertTrue(pbkdf2_sha256.verify(plaintext, hashed_password))

    def test_hidden_password(self):
        """Assert that password hash can not be retrieved."""
        user_id = self.new_user(password="somepw")['_id']

        # Normal get
        r = self.api.get("/users/%s" % user_id, status_code=200).json

        self.assertNotIn('password', r.keys())

        # Try to force projection
        # This should return a 403 error because we are trying to set a
        # forbidden projection
        self.api.get(u'/users/%s?projection={"password": 1}' % user_id,
                     status_code=403).json

    def test_hash_on_insert(self):
        """Test Hash insert function.

        Because of how Eve handles hooks, they all modify the input arguments.

        Need app context to find config.
        """
        with self.app.app_context():
            # First test hash on insert
            items = [
                {'password': self.pw_1},
                {'password': self.pw_2}
            ]

            # Hash passwords in list items
            hash_on_insert(items)

            # Check hashed
            self.assertVerify(self.pw_1, items[0]['password'])
            self.assertVerify(self.pw_2, items[1]['password'])

    def test_hash_on_update(self):
        """Test hash on update. Works like test for hash on insert."""
        with self.app.app_context():
            data = {'password': self.pw_1}

            # Second param is original data, but the hash function ignores
            # it so we can just set it to None
            hash_on_update(data, None)

            # Check hash
            self.assertVerify(self.pw_1, data['password'])

    def test_verify_hash(self):
        """Test verify hash.

        Also needs app context to access config.
        """
        with self.app.app_context():
            hashed = self.app.config['PASSWORD_CONTEXT'].encrypt(
                self.pw_1)

            # Correct password
            self.assertTrue(
                verify_password({'password': hashed}, self.pw_1)
            )

            # Wrong password
            self.assertFalse(
                verify_password({'password': hashed}, "NotThePassword")
            )

    def test_verify_hash_rehashes_weak_password(self):
        """Test that verify_password rehashes password.

        This is supposed to happen if the security of the crypt context
        is increased.

        Needs request context because Eve requires this for "patch_internal"
        which is used to updated the hash.
        """
        with self.app.test_request_context():
            db = self.db['users']

            weak_hash = self.weak_context.encrypt(self.pw_1)

            # Add a user with to db. use password hashed with weak context
            user_id = db.insert({
                'password': weak_hash
            })

            user = db.find_one({'_id': ObjectId(user_id)})

            # Set context to "strong" context
            self.app.config['PASSWORD_CONTEXT'] = self.strong_context

            # Verify password, should be true
            self.assertTrue(verify_password(user, self.pw_1))

            # The verify_password should now have rehashed the password

            # Get new user data
            user = db.find_one({'_id': ObjectId(user_id)})

            # Password hash has changed
            self.assertNotEqual(user['password'], weak_hash)

            # Password is still valid
            self.assertVerify(self.pw_1, user['password'])

    def assertVerifyDB(self, user_id, plaintext):
        """Check that the stored password was hashed correctly.

        Shorthand to query db and compare.

        Args:
            user_id (str): The user.
            hashed_password (str): The hash which should be stored

        Returns:
            bool: True if hashed correctly.
        """
        user = self.db["users"].find_one({'_id': ObjectId(user_id)})

        self.assertTrue(pbkdf2_sha256.verify(plaintext, user['password']))

    def test_hash_hooks(self):
        """Test hash hooks.

        Assert passwort is hashed when user is created or updated through
        the api.
        """
        post_data = {
            'firstname': 'T',
            'lastname': 'Estuser',
            'gender': 'female',
            'membership': 'regular',
            'email': 'test@user.amiv',
            'password': self.pw_1
        }

        user = self.api.post("/users", data=post_data, status_code=201).json

        self.assertVerifyDB(user['_id'], self.pw_1)

        patch_data = {'password': self.pw_2}

        headers = {'If-Match': user['_etag']}
        user = self.api.patch("/users/%s" % user['_id'],
                              headers=headers, data=patch_data,
                              status_code=200).json

        self.assertVerifyDB(user['_id'], self.pw_2)

    def test_hash_update_on_login(self):
        """Test that passwords are rehashed when needed on login.

        TODO(Alex): Implement as soon as auth is working.
        """
        pass


class UserFieldPermissions(utils.WebTest):
    """Test field permissions.

    Some fields can be changed by the user, some only by admins.
    """

    def test_change_by_user(self):
        """User can change password, email. and rfid."""
        pass

    def test_not_patchable_unless_admin(self):
        """Admin can change everything, user not."""
        user = self.new_user(gender='female', department='itet',
                             membership="regular",
                             nethz='user', password="userpass")
        user_id = str(user['_id'])
        user_etag = user['_etag']  # This way we can overwrite it later easily

        bad_changes = [
            {"firstname": "new_name"},
            {"lastname": "new_name"},
            {"legi": "10000000"},
            {"nethz": "coolkid"},
            {"department": "mavt"},
            {"gender": "male"},
            {"membership": "none"},
        ]

        def patch(data, token, etag, status_code):
            """Shortcut for patch."""
            return self.api.patch("/users/" + user_id, token=token,
                                  headers={"If-Match": etag},
                                  data=data,
                                  status_code=status_code).json

        # The user can change none of those fields
        user_token = self.get_user_token(user_id)
        for bad_data in bad_changes:
            patch(bad_data, user_token, user_etag, 422)

        # The admin can
        admin_token = self.get_root_token()
        for data in bad_changes:
            response = patch(data, admin_token, user_etag, 200)
            # Since the change is successful we need the new etag
            user_etag = response['_etag']
