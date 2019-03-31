# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test the fixture system for tests."""

from bson import ObjectId

from amivapi.tests.utils import WebTest


class FixtureTest(WebTest):
    """Test the function to add test fixtures."""

    def test_fixtures_random_generator(self):
        """Test that the fixture system generates valid documents."""
        for resource in self.app.config['DOMAIN']:
            self.load_fixture({resource: {}})

    def test_fixtures_content(self):
        """Test that loaded fixtures have the specified content."""
        fixture = {
            'users': [
                {
                    '_id': ObjectId('000000000000000000000001'),
                    'nethz': 'pablo'
                }
            ]
        }

        self.load_fixture(fixture)

        # Find all users
        users = self.db['users'].find()

        self.assertEqual(users.count(), 1)
        self.assertEqual(users[0]['nethz'], 'pablo')
