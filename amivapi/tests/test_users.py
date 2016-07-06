# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for user module.

Includes item and field permissions as well as password hashing.
"""


from amivapi.tests import util
from amivapi.users import hash_on_insert, hash_on_update, verify_password

from passlib.context import CryptContext
from passlib.hash import pbkdf2_sha256


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

    def test_root_user_is_in_db(self):
        """Test if root user is in the db.

        TODO(Alex): Implement
        """
        pass


class PasswordHashing(util.WebTestNoAuth):
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

    def assertHashed(self, plaintext, hashed_password):
        """Assert the hash matches the password."""
        assert pbkdf2_sha256.verify(plaintext, hashed_password)

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
            self.assertHashed(self.pw_1, items[0]['password'])
            self.assertHashed(self.pw_2, items[1]['password'])

    def test_hash_on_update(self):
        """Test hash on update. Works like test for hash on insert."""
        with self.app.app_context():
            data = {'password': self.pw_1}

            # Second param is original data, but the hash function ignores
            # it so we can just set it to None
            hash_on_update(data, None)

            # Check hash
            self.assertHashed(self.pw_1, data['password'])

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

            # Add a user with to db. use password hashed with weak context
            user = db.insert({
                'password': self.weak_context.encrypt(self.pw_1)
            })

            print(user)

            # Set context to "strong" context
            self.app.config['PASSWORD_CONTEXT'] = self.strong_context

    def assertHashedInDb(self, user_id, plaintext):
        """Check that the stored password was hashed correctly.

        Shorthand to query db and compare.

        Args:
            user_id (str): The user.
            hashed_password (str): The hash which should be stored

        Returns:
            bool: True if hashed correctly.
        """
        user = self.db["users"].find_one(_id=user_id)

        assert pbkdf2_sha256.verify(plaintext, user['password'])

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

        self.assertHashedInDb(user['_id'], self.pw_1)

        patch_data = {'password': self.pw_2}

        headers = {'If-Match': user['_etag']}
        user = self.api.patch("/users/%s" % user['_id'],
                              headers=headers, data=patch_data,
                              status_code=200).json

        self.assertHashedInDb(user['_id'], self.pw_2)

    def test_hash_update_on_login(self):
        """Test that passwords are rehashed when needed on login.

        TODO(Alex): Implement as soon as auth is working.
        """
        pass


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
