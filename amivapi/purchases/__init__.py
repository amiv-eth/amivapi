# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Purchases module.

Since there are no hooks or anything everything is just in here.
"""

from amivapi.utils import register_domain

from amivapi.auth import AmivTokenAuth


class PurchaseAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id):
        return {'user': user_id}


purchasedomain = {
    'purchases': {
        'description': 'A beer machine or kaffi machine transaction. Users '
        'should be able to get beer or kaffi, if their last timestamp is older '
        'than one day and they are AMIV members. This resource is used to log '
        'their purchases.',

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET'],

        'authentication': PurchaseAuth,

        'schema': {
            'timestamp': {
                'nullable': False,
                'required': True,
                'type': 'datetime',
                'unique': False
            },
            'product': {
                'maxlength': 6,
                'nullable': False,
                'required': True,
                'type': 'string',
                'unique': False,
                'not_patchable_unless_admin': True,
                'allowed': ['beer', 'coffee']
            },
            'user': {
                'nullable': False,
                'required': True,
                'type': 'objectid',
                'unique': False,
                'data_relation': {
                    'resource': 'users',
                    'field': '_id',
                    'embeddable': True
                },
            }
        }
    }
}


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, purchasedomain)
