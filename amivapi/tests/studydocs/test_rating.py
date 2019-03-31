# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for studydocuments rating."""

from amivapi.studydocs.rating import lower_confidence_bound
from amivapi.tests.utils import WebTestNoAuth


class StudydocsRatingTest(WebTestNoAuth):
    """Test rating computation."""

    def test_no_rating(self):
        """Without any votes, the rating is None."""
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
        ]:
            bound = lower_confidence_bound(upvotes, downvotes)
            self.assertAlmostEqual(rating, bound, 2)

    def test_rating(self):
        """Test that the rating is correctly attached to the studydoc."""
        doc = self.new_object('studydocuments')
        lookup = {'studydoc': str(doc['_id'])}

        response = self.api.get('/studydocuments/' + str(doc['_id']),
                                status_code=200)
        # No ratings yet
        self.assertIsNone(response.json['rating'])

        self.load_fixture({
            'users': [{}],
            'studydocratings': [{'rating': 'up', **lookup}],
        })

        response = self.api.get('/studydocuments/' + str(doc['_id']),
                                status_code=200)
        self.assertAlmostEqual(response.json['rating'], 0.38, 2)
