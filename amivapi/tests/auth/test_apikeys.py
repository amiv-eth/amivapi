# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test apikey authorization."""

from amivapi.tests.utils import WebTest, WebTestNoAuth


class ApiKeyMethodsTest(WebTest):
    """Apikey auth test class.

    Since they grant possible all permissions, make extra sure that auth works
    right.
    """
    def _prepare_tokens_and_key(self):
        user = self.new_object('users')
        user_token = self.get_user_token(user['_id'])
        admin_token = self.get_root_token()
        key = self.new_object('apikeys')
        return (key, user_token, admin_token)

    def test_only_admin_can_read_item(self):
        """GET on item endpoint only for admins."""
        (key, user_token, admin_token) = self._prepare_tokens_and_key()
        url = "/apikeys/%s" % key['_id']

        self.api.get(url, status_code=401)
        self.api.get(url, token=user_token, status_code=403)
        self.api.get(url, token=admin_token, status_code=200)

    def test_only_admin_can_read_resource(self):
        """GET on resource only for admins."""
        (_, user_token, admin_token) = self._prepare_tokens_and_key()
        url = "/apikeys"

        self.api.get(url, status_code=401)
        self.api.get(url, token=user_token, status_code=403)
        self.api.get(url, token=admin_token, status_code=200)

    def test_only_admin_can_create(self):
        """POST only for admins."""
        (_, user_token, admin_token) = self._prepare_tokens_and_key()
        data = {'name': 'super_backdoor_key',
                'permissions': {'apikeys': 'readwrite'}}
        url = "/apikeys"

        self.api.post(url, data=data, status_code=401)
        self.api.post(url, data=data, token=user_token, status_code=403)
        self.api.post(url, data=data, token=admin_token, status_code=201)

    def test_only_admin_can_update(self):
        """PATCH only for admins."""
        (key, user_token, admin_token) = self._prepare_tokens_and_key()
        data = {'name': 2 * key['name']}  # New: Twice the fun!
        url = "/apikeys/%s" % key['_id']
        etag = {'If-Match': key['_etag']}

        self.api.patch(url, data=data, headers=etag, status_code=401)
        self.api.patch(url, data=data, headers=etag, token=user_token,
                       status_code=403)
        self.api.patch(url, data=data, headers=etag, token=admin_token,
                       status_code=200)

    def test_only_admin_can_delete(self):
        """PATCH only for admins."""
        (key, user_token, admin_token) = self._prepare_tokens_and_key()
        url = "/apikeys/%s" % key['_id']
        etag = {'If-Match': key['_etag']}

        self.api.delete(url, headers=etag, status_code=401)
        self.api.delete(url, headers=etag, token=user_token, status_code=403)
        self.api.delete(url, headers=etag, token=admin_token, status_code=204)


class ApiKeyPermissionsTest(WebTest):
    """Test that an api key grants permissions."""
    def test_read_permission(self):
        """Read permission allows get, but no writing."""
        key = self.new_object("apikeys", permissions={'apikeys': 'read'})
        token = key['token']
        item_url = '/apikeys/%s' % key['_id']

        self.api.get('/apikeys', token=token, status_code=200)
        self.api.get(item_url, token=token, status_code=200)

        self.api.post('/apikeys', data={}, token=token, status_code=403)

    def test_readwrite_permission(self):
        """Readwrite permission allows everything."""
        key = self.new_object("apikeys", permissions={'apikeys': 'readwrite'})
        token = key['token']
        item_url = '/apikeys/%s' % key['_id']
        etag = {'If-Match': key['_etag']}

        self.api.get('/apikeys', token=token, status_code=200)
        self.api.get(item_url, token=token, status_code=200)

        self.api.delete(item_url, headers=etag, token=token, status_code=204)

    def test_different_resource(self):
        """Test that apikeys for different resources have no effect."""
        key = self.new_object("apikeys", permissions={'users': 'readwrite'})
        token = key['token']

        self.api.get('/apikeys', token=token, status_code=403)


class ApiKeyModelTests(WebTestNoAuth):
    """Test that tokens are correctly generated and permissions validation."""
    def test_token_generation(self):
        """Use a batch post to verify all items get distinct keys."""
        data = [{'name': 'key1', 'permissions': {'apikeys': 'read'}},
                {'name': 'key2', 'permissions': {'apikeys': 'readwrite'}}]

        result = self.api.post("/apikeys", data=data).json
        tokens = [item['token'] for item in result['_items']]

        self.assertNotEqual(tokens[0], tokens[1])
        # Assert keys are not empty
        for token in tokens:
            self.assertTrue(len(token) > 0)

    def test_permission_validation(self):
        wrong_key = {'name': 'k1', 'permissions': {'notAResource': 'read'}}
        wrong_value = {'name': 'k2', 'permissions': {'apikeys': 'roodwroat'}}
        read_ok = {'name': 'k3', 'permissions': {'apikeys': 'read'}}
        readwrite_ok = {'name': 'k4', 'permissions': {'apikeys': 'readwrite'}}

        self.api.post("/apikeys", data=wrong_key, status_code=422)
        self.api.post("/apikeys", data=wrong_value, status_code=422)
        self.api.post("/apikeys", data=read_ok, status_code=201)
        self.api.post("/apikeys", data=readwrite_ok, status_code=201)
