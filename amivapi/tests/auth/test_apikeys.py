# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test apikey authorization."""

from amivapi.tests.utils import WebTest
import os
from ruamel import yaml
import tempfile


class ApiKeyTest(WebTest):
    """Apikey auth test class."""

    token = 'ABCDEFG'
    APIKEYS = {
        'testkey': {
            'token': token,
            'permissions': {
                'sessions': 'read'
            }
        }
    }

    def setUp(self):
        """Create temp apikey file before normal setup."""
        with tempfile.NamedTemporaryFile(
                mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(self.APIKEYS, f, default_flow_style=False)
            self.test_config['APIKEY_FILENAME'] = f.name

        super(ApiKeyTest, self).setUp()

    def tearDown(self):
        """Remove key file."""
        os.remove(self.test_config['APIKEY_FILENAME'])

        super(ApiKeyTest, self).tearDown()

    def test_apikey_gives_permission(self):
        """Test that APIKEY gives specified permissions."""
        self.load_fixture({
            'users': [{}, {}],
            'sessions': [{}, {}]
        })

        sessions = self.api.get('/sessions', token=self.token,
                                status_code=200).json['_items']

        self.assertEqual(len(sessions), 2)

        self.api.delete('/sessions/%s' % sessions[0]['_id'], token=self.token,
                        headers={'If-Match': sessions[0]['_etag']},
                        status_code=403)

        self.api.get('/users', token=self.token, status_code=403)
