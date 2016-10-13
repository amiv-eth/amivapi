# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test the fixture system for tests"""

from copy import deepcopy
from bson import ObjectId

from amivapi.tests.utils import WebTest
from eve.io.mongo import Validator


class FixtureTest(WebTest):
    def test_fixtures_random_generator(self):
        """Test that the fixture system generates valid documents"""
        # create a fixture, which creates all kinds of objects
        fixture = {}
        for resource in self.app.config['DOMAIN']:
            fixture[resource] = [{}]

        self.load_fixture(fixture)

    def test_fixtures_content(self):
        """Test that loaded fixtures have the specified content"""
        fixture = {
            'users': [
                {
                    '_id': ObjectId('000000000000000000000001'),
                    'nethz': 'pablo'
                }
            ]
        }

        self.load_fixture(fixture)

        # Find all non root users
        users = self.db['users'].find(
            {'_id': {'$ne': self.app.config['ROOT_ID']}})

        self.assertEqual(users.count(), 1)
        self.assertEqual(users[0]['nethz'], 'pablo')
