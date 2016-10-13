# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test for cascading deletes"""

from bson import ObjectId

from amivapi.tests.utils import WebTestNoAuth


class CascadingDeleteTest(WebTestNoAuth):

    def test_delete_cascades(self):
        """Test that deletion of an object deletes referencing objects, when
        cascading is enabled"""

        self.load_fixture({
            'users': [
                {
                    '_id': 'deadbeefdeadbeefdeadbeef',
                    'nethz': 'user1'
                },
                {
                    '_id': 'deadbeefdeadbeefdeadbee3',
                    'nethz': 'user2'
                }
            ],
            'sessions': [
                {
                    '_id': 'deadbeefdeadbeefdeadbee2',
                    'username': 'user1'
                },
                {
                    '_id': 'deadbeefdeadbeefdeadbee1',
                    'username': 'user2'
                }
            ]
        })

        user1 = self.api.get("/users/deadbeefdeadbeefdeadbeef",
                             status_code=200).json

        self.api.delete("/users/deadbeefdeadbeefdeadbeef",
                        headers={'If-Match': user1['_etag']},
                        status_code=204)

        sessions = self.db['sessions'].find()
        self.assertEqual(sessions.count(), 1)

        sessions = self.db['sessions'].find({
            'user': ObjectId('deadbeefdeadbeefdeadbeef')})
        self.assertEqual(sessions.count(), 0)
