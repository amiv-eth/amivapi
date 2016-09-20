# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Purchases module.

Since there are no hooks or anything everything is just in here.
"""

from amivapi.utils import register_domain

purchasedomain = {
    'purchases': {'datasource': {'projection': {'_author': 1,
                                                'id': 1,
                                                'slot': 1,
                                                'timestamp': 1,
                                                'type': 1,
                                                'user_id': 1},
                                 'source': 'Purchase'},
                  'description': {
                      'fields': {
                          'slot': 'Slot in the machine which was '
                          'purchased(different items, which may have '
                          'different prices).'},
                      'general': 'A beer machine or kaffi machine '
                      'transaction. Users should be able to get beer or '
                      'kaffi, if their last timestamp is older than one day '
                      'and they are AMIV members. This resource is used to '
                      'log their purchases.'},
                  'item_lookup': True,
                  'item_lookup_field': '_id',
                  'item_url': 'regex("[0-9]+")',
                  'owner': ['user_id'],
                  'owner_methods': ['GET'],
                  'public_item_methods': [],
                  'public_methods': [],
                  'registered_methods': [],
                  'schema': {'_author': {'data_relation': {'embeddable': False,
                                                           'resource': 'users'},
                                         'nullable': True,
                                         'readonly': True,
                                         'required': False,
                                         'type': 'objectid',
                                         'unique': False},
                             'slot': {'nullable': True,
                                      'required': False,
                                      'type': 'integer',
                                      'unique': False},
                             'timestamp': {'nullable': True,
                                           'required': False,
                                           'type': 'datetime',
                                           'unique': False},
                             'type': {'maxlength': 5,
                                      'nullable': True,
                                      'required': False,
                                      'type': 'string',
                                      'unique': False},
                             'user_id': {'nullable': True,
                                         'required': False,
                                         'type': 'integer',
                                         'unique': False}}}}


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, purchasedomain)
