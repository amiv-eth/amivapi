# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Studydoc rating computation."""

from bson import ObjectId
from flask import current_app
from math import sqrt


def lower_confidence_bound(upvotes, downvotes, z=1.28):
    """Compute the lower bound of the wilson confidence interval is returned,
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


def add_rating(item):
    """Computes the rating for a study document."""
    ratings = current_app.data.driver.db['studydocratings']
    lookup = {'studydoc': ObjectId(item['_id'])}

    upvotes = ratings.count_documents({'rating': 'up', **lookup})
    downvotes = ratings.count_documents({'rating': 'down', **lookup})

    item['rating'] = lower_confidence_bound(upvotes, downvotes)


def add_rating_collection(response):
    for item in response['_items']:
        add_rating(item)
