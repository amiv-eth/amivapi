# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Studydoc rating computation.

For the rating, we use the lower bound of a confidence interval around
the 'naive' average vote, which accounts for the number of votes.

The rating for a study document is updated each time a study doc rating is
for the respective document is POSTed or PATCHed. The value is then written
to the database to allow sorting of study documents by rating.
"""

from flask import current_app
from math import sqrt

from amivapi.utils import get_id


def compute_rating(upvotes, downvotes, z=1.28):
    """Compute the rating.

    Concretely, the lower bound of the wilson confidence interval is returned,
    which takes the number of votes into account. [1]

    We use z = 1.28 by default, which corresponds to a 80% confidence interval
    (As there are only a few votes, we do not want to be overly cautious).

    [1]: http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
    """
    total = upvotes + downvotes
    if not total:
        return

    p = upvotes / total
    bound = ((p + (z**2)/(2*total) -
              z * sqrt((p * (1-p) + (z**2)/(4*total)) / total)) /
             (1 + (z**2)/total))

    # Ensure that the bound is not below 0
    return max(bound, 0)


def _update_rating(studydoc_id):
    """Computes the rating for a study document."""
    docs = current_app.data.driver.db['studydocuments']
    ratings = current_app.data.driver.db['studydocumentratings']
    lookup = {'studydocument': studydoc_id}

    # Check votes
    upvotes = ratings.count_documents({'rating': 'up', **lookup})
    downvotes = ratings.count_documents({'rating': 'down', **lookup})

    # Compute rating and write to database
    rating = compute_rating(upvotes, downvotes)
    docs.update_one({'_id': studydoc_id}, {'$set': {'rating': rating}})


def init_rating(items):
    """On creating of a study-document, set the rating to None."""
    for item in items:
        item['rating'] = None


def update_rating_post(items):
    """Rating update hook for POST requests."""
    for item in items:
        _update_rating(get_id(item['studydocument']))


def update_rating_patch(updates, original):
    """Rating update hook for PATCH requests."""
    _update_rating(get_id(updates['studydocument'])
                   if 'studydocument' in updates else
                   get_id(original['studydocument']))


def update_rating_delete(item):
    """Rating update hook for DELETE requests."""
    _update_rating(get_id(item['studydocument']))
