# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for studydocuments rating."""

from amivapi.studydocs.rating import lower_confidence_bound
from amivapi.tests.utils import WebTest, WebTestNoAuth


class StudydocsRatingTest(WebTestNoAuth):
    """Test rating computation."""

    def test_no_rating(self):
        """Without any votes, the `rating` is in the document, and is None."""
        doc = self.new_object('studydocuments')

        response = self.api.get('/studydocuments/' + str(doc['_id']),
                                status_code=200)

        self.assertIsNone(response.json['rating'])

    def test_bound(self):
        """Without any votes, the rating is None."""
        for upvotes, downvotes, rating in [
            (1, 0, 0.38),
            (5, 0, 0.75),
            (10, 0, 0.86),
            (1, 1, 0.16),
            (5, 2, 0.47),
            (5, 5, 0.31),
            (50, 50, 0.44),
            (0, 1, 0.0),
            (0, 5, 0.0),
            (0, 10, 0.0),
        ]:
            bound = lower_confidence_bound(upvotes, downvotes)
            self.assertAlmostEqual(rating, bound, 2)

    def test_rating(self):
        """Test that the rating is correctly attached to the studydoc."""
        doc = self.new_object('studydocuments')
        lookup = {'studydocument': str(doc['_id'])}

        response = self.api.get('/studydocuments/' + str(doc['_id']),
                                status_code=200)
        # No ratings yet
        self.assertIsNone(response.json['rating'])

        self.load_fixture({
            'users': [{}],
            'studydocumentratings': [{'rating': 'up', **lookup}],
        })

        response = self.api.get('/studydocuments/' + str(doc['_id']),
                                status_code=200)
        self.assertAlmostEqual(response.json['rating'], 0.38, 2)

    def test_sort_by_rating(self):
        """Ensure that sorting by rating works."""
        ids = [24 * '0', 24 * '1', 24 * '2']
        self.load_fixture({
            'users': [{}],
            'studydocuments': [
                {'_id': ids[0]}, {'_id': ids[1]}, {'_id': ids[2]}
            ],
            'studydocumentratings': [
                # Rate such that:
                # 0: No rating, 1: Low rating, 2: High rating
                {'studydocument': ids[2], 'rating': 'up'},
                {'studydocument': ids[1], 'rating': 'down'},
            ],
        })
        response = self.api.get('/studydocuments?sort=rating', status_code=200)
        for (item, expected_id) in zip(response.json['_items'], ids):
            self.assertEqual(item['_id'], expected_id)

        # Also test reverse order, to ensure that it was no accident
        response = self.api.get('/studydocuments?sort=-rating', status_code=200)
        for (item, expected_id) in zip(response.json['_items'], ids[::-1]):
            self.assertEqual(item['_id'], expected_id)

    def _assert_rating(self, studydoc_id, rating):
        response = self.api.get('/studydocuments/' + studydoc_id,
                                status_code=200)
        self.assertAlmostEqual(response.json['rating'], rating, 2)

    def test_new_vote(self):
        """POSTing a new vote updates the rating."""
        user = str(self.new_object('users')['_id'])
        doc = str(self.new_object('studydocuments')['_id'])
        self._assert_rating(doc, None)

        data = {'user': user, 'studydocument': doc, 'rating': 'up'}
        self.api.post('/studydocumentratings', data=data, status_code=201)
        self._assert_rating(doc, 0.38)

    def test_change_vote(self):
        """PATCHing an existing vote updates the rating."""
        self.new_object('users')
        doc = str(self.new_object('studydocuments')['_id'])
        rating = self.new_object('studydocumentratings', rating='up')
        self._assert_rating(doc, 0.38)

        headers = {'If-Match': rating['_etag']}
        data = {'rating': 'down'}
        self.api.patch('/studydocumentratings/' + str(rating['_id']),
                       data=data, headers=headers, status_code=200)
        self._assert_rating(doc, 0.0)

    def test_delete_vote(self):
        """DELETEing votes update the rating."""
        user_1, user_2 = self.load_fixture({'users': [{}, {}]})
        doc = str(self.new_object('studydocuments')['_id'])
        rating_1, rating_2 = self.load_fixture({
            'studydocumentratings': [
                {'user': str(user_1['_id']), 'rating': 'up'},
                {'user': str(user_2['_id']), 'rating': 'down'}
            ]
        })
        self._assert_rating(doc, 0.16)

        self.api.delete('/studydocumentratings/' + str(rating_2['_id']),
                        headers={'If-Match': rating_2['_etag']},
                        status_code=204)
        self._assert_rating(doc, 0.38)

        # After the last rating get's deleted, the rating is `None` again
        self.api.delete('/studydocumentratings/' + str(rating_1['_id']),
                        headers={'If-Match': rating_1['_etag']},
                        status_code=204)
        self._assert_rating(doc, None)

    def test_rate_once(self):
        """Every user can rate a document only once."""
        user = str(self.new_object('users')['_id'])
        doc = str(self.new_object('studydocuments')['_id'])

        data = {'user': user, 'studydocument': doc, 'rating': 'up'}
        self.api.post('/studydocumentratings', data=data, status_code=201)
        self.api.post('/studydocumentratings', data=data, status_code=422)


class StudydocsRatingAuthTest(WebTest):
    """Test rating permissions and visibility."""

    def test_see_own(self):
        """Users can only see their own ratings."""
        user_1, user_2 = self.load_fixture({'users': [{}, {}]})
        self.new_object('studydocuments')
        rating_1, rating_2 = self.load_fixture({
            'studydocumentratings': [
                {'user': str(user_1['_id']), 'rating': 'up'},
                {'user': str(user_2['_id']), 'rating': 'down'}
            ]
        })

        token = self.get_user_token(rating_1['user'])

        # Resource
        response = self.api.get('/studydocumentratings',
                                token=token, status_code=200)
        ids = [item['_id'] for item in response.json['_items']]
        self.assertIn(str(rating_1['_id']), ids)
        self.assertNotIn(str(rating_2['_id']), ids)

        # Item
        self.api.get('/studydocumentratings/' + str(rating_1['_id']),
                     token=token, status_code=200)
        self.api.get('/studydocumentratings/' + str(rating_2['_id']),
                     token=token, status_code=404)

    def test_create(self):
        """Users can only create ratings for themselves."""
        user_1, user_2 = self.load_fixture({'users': [{}, {}]})
        doc = str(self.new_object('studydocuments')['_id'])

        data_1 = {'studydocument': doc, 'user': str(user_1['_id']),
                  'rating': 'up'}
        data_2 = {'studydocument': doc, 'user': str(user_2['_id']),
                  'rating': 'up'}
        token = self.get_user_token(user_1['_id'])
        self.api.post('/studydocumentratings', data=data_1, token=token,
                      status_code=201)
        self.api.post('/studydocumentratings', data=data_2, token=token,
                      status_code=422)

    def test_modify_own(self):
        """Users can only patch their own ratings."""
        user_1, user_2 = self.load_fixture({'users': [{}, {}]})
        self.new_object('studydocuments')
        rating_1, rating_2 = self.load_fixture({
            'studydocumentratings': [
                {'user': str(user_1['_id']), 'rating': 'down'},
                {'user': str(user_2['_id']), 'rating': 'down'}
            ]
        })

        token = self.get_user_token(rating_1['user'])
        updates = {'rating': 'up'}

        self.api.patch('/studydocumentratings/' + str(rating_1['_id']),
                       data=updates, token=token, status_code=200,
                       headers={'If-Match': rating_1['_etag']})
        # Cannot even see other rating, so a 404 is returned
        self.api.patch('/studydocumentratings/' + str(rating_2['_id']),
                       data=updates, token=token, status_code=404,
                       headers={'If-Match': rating_2['_etag']})

    def test_delete_own(self):
        """Users can only delete their own ratings."""
        user_1, user_2 = self.load_fixture({'users': [{}, {}]})
        self.new_object('studydocuments')
        rating_1, rating_2 = self.load_fixture({
            'studydocumentratings': [
                {'user': str(user_1['_id']), 'rating': 'down'},
                {'user': str(user_2['_id']), 'rating': 'down'}
            ]
        })

        token = self.get_user_token(rating_1['user'])

        self.api.delete('/studydocumentratings/' + str(rating_1['_id']),
                        token=token, status_code=204,
                        headers={'If-Match': rating_1['_etag']})
        # Cannot even see other rating, so a 404 is returned
        self.api.delete('/studydocumentratings/' + str(rating_2['_id']),
                        token=token, status_code=404,
                        headers={'If-Match': rating_2['_etag']})