# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for user module.

Includes item and field permissions as well as password hashing.
"""

from bson import ObjectId

from amivapi.tests import utils


class UserTest(utils.WebTestNoAuth):
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

        # Get new etag
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

        Since objectid strings are 24 characters long, the root user id
        string is just 24 zeros
        """
        root_id = 24 * "0"

        query = self.db['users'].find_one({'_id': ObjectId(root_id)})
        self.assertTrue(query is not None)

        # Also test that eve can access it without error
        self.api.get("/users/" + root_id, status_code=200)
