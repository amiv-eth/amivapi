# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for blacklist resource."""

from amivapi.tests.utils import WebTest


class BlacklistModelTest(WebTest):
    """Test blacklist permissions.

    Admins can see all blacklist entries, a user only his own.
    """

    def test_users_cant_create(self):
        """Normal users can't create anything."""
        self.load_fixture({'users': [{'_id': 24 * "0"}]})  # Create a user
        self.api.post("/blacklist", token=self.get_user_token(24 * "0"),
                      data={}, status_code=403)

    def test_create(self):
        """Test to create blaklist entry."""
        self.load_fixture({'users': [{'_id': 24 * "0"}]})  # Create a user
        data = {
            'user': 24 * "0",
            'reason': "Test",
            'price': 0,
            'start_time': "2019-03-29T00:00:00Z",
            'end_time': "2019-03-30T00:00:00Z",
        }
        self.api.post("/blacklist", data=data, token=self.get_root_token(),
                      status_code=201)

    def test_item_write(self):
        """Admin can patch and delete, user can't."""
        user_id = 24 * '0'
        blacklist_id = 24 * '1'

        self.load_fixture({'users': [{'_id': user_id}]})  # Create user
        r = self.load_fixture({
                'blacklist': [{
                    '_id': blacklist_id,
                    'user': user_id,
                    'reason': "Test1"}]
            })  # Creat blacklist entry

        etag = r[0]['_etag']
        user_token = self.get_user_token(user_id)

        patch = {'reason': "Test2"}
        header = {'If-Match': etag}

        self.api.patch("/blacklist/%s" % blacklist_id, data=patch,
                       headers=header, token=user_token, status_code=403)

        r = self.api.patch("/blacklist/%s" % blacklist_id, data=patch,
                           headers=header, token=self.get_root_token(),
                           status_code=200)

        header['If-Match'] = r.json['_etag']

        self.api.delete("/blacklist/%s" % blacklist_id, headers=header,
                        token=user_token, status_code=403)
        self.api.delete("/blacklist/%s" % blacklist_id, headers=header,
                        token=self.get_root_token(), status_code=204)

    def test_lookup_filter(self):
        """Test if a user can only see his own blacklist entry."""
        user_id = 24*"0"
        other_user_id = 24*"1"
        blacklist_id = 24*"2"

        self.load_fixture({
            # Create two users
            'users':
                [{'_id': user_id},
                 {'_id': other_user_id}],
            # Creat blacklist entry
            'blacklist':
                [{'_id': blacklist_id,
                 'user': user_id}]
            })

        # Resource lookups
        r = self.api.get("/blacklist", token=self.get_user_token(user_id),
                         status_code=200).json
        self.assertIn(blacklist_id, r['_items'][0]['_id'])

        r = self.api.get("/blacklist", token=self.get_user_token(other_user_id),
                         status_code=200).json
        self.assertTrue(r['_items'] == [])

        # Item lookups
        self.api.get("/blacklist/%s" % blacklist_id,
                     token=self.get_user_token(user_id), status_code=200)

        self.api.get("/blacklist/%s" % blacklist_id,
                     token=self.get_user_token(other_user_id), status_code=404)
