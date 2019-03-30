# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Blacklist settings.

Contains model for blacklist.
"""
from amivapi.blacklist.authorization import BlacklistAuth


blacklist_description = ("""
People normally get blacklisted if they don't appear to an event they signed up
for, but other cases could be possible (Bad behaviour, etc). Once on the
blacklist, they shouldn't be able to sign up for any event until they pay
for that event or do something else the board decides (e.g. help at an event).
""")

blacklist = {

    'blacklist': {
        'description': blacklist_description,

        'resource_methods': ['POST', 'GET'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': BlacklistAuth,

        'schema': {
            'user': {
                "description": "The user who is blacklisted",
                "example": "5bd19211d57724603b489882",

                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                    'cascade_delete': True,
                },

                'type': 'objectid',
                'nullable': False,
                'required': True
            },
            'reason': {
                'title': 'Reason',
                'description': 'The reason for the blacklist entry',
                'example': 'An Event xy nicht erschienen',

                'nullable': False,
                'type': 'string',
                'maxlength': 100,
                'required': True
            },
            'price': {
                'description': "The price",
                'example': "5",

                'type': 'integer',
                'nullable': True,
                'required': True,
            },
            'start_time': {
                'description': 'The date on which the user was blacklisted',
                'example': '2018-10-11T00:00:00Z',

                'type': 'datetime',
                'nullable': False,
                'required': True,
            },
            'end_time': {
                'description':
                'The date on which the user is deleted from the blacklist',
                'example': '2018-10-11T00:00:00Z',

                'type': 'datetime',
                'nullable': True,
                'default': None,
            }
        }
    }
}
