# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Beverages module.

Since there are no hooks or anything everything is just in here.
"""
from amivapi.auth import AmivTokenAuth
from amivapi.utils import register_domain


class BeveragesAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id):
        """Users can only access their own consumption."""
        return {'user': user_id}


beveragesdomain = {
    'beverages': {
        'description': 'A beer- or coffee machine transaction logged with '
                       'timestamp. Can  be used to decide whether the user '
                       'can receive a free beverage or not, e.g. because a '
                       'beverage was already retrieved on the same day.',
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET'],

        'authentication': BeveragesAuth,

        'schema': {
            'timestamp': {
                'description': 'Time when the beverage was retrieved.',

                'nullable': False,
                'required': True,
                'type': 'datetime',
                'unique': False
            },
            'product': {
                'description': 'Which type of beverage was retrieved.',

                'nullable': False,
                'required': True,
                'type': 'string',
                'unique': False,
                'not_patchable_unless_admin': True,
                'allowed': ['beer', 'coffee']
            },
            'user': {
                'description': 'The user retrieving the beverage.',
                'example': 'dbb46b84d91d4098a1de42ad',

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
    """Register resource."""
    register_domain(app, beveragesdomain)
