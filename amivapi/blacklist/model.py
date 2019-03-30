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

An entry on the blacklist always has a reason and a start_date (normally the
date of the event where the user didn't appear), most often also a price the
user has to pay to be removed from the blacklist.

One person can have multiple blacklist entries and old entries are not deleted,
but marked with an end date.

Only users with admin-rights for the blacklist can see all entries and create
new ones/edit them. A single user only has the right to see his own blacklist
entries, but he cannot edit them.
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

                'empty': False,
                'nullable': False,
                'type': 'string',
                'maxlength': 100,
                'required': True
            },
            'price': {
                'description': 'The price the user has to pay to be removed (in'
                ' rappen, e.g. 500 for 5 CHF) from the blacklist. Normally, but'
                ' not necessarily, this is the event price. If there is no '
                'price to pay, e.g. if the user has to help somewhere instead '
                'of paying, the value can be set to Null.',
                'example': "500",

                'type': 'integer',
                'nullable': True,
                'required': False,
                'default': None,
                'min': 1,
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
                'The date on which this blacklist entry is resolved, i.e. the '
                'user has paid the price or fulfilled any other task the board '
                'decided. The user can still have another blacklist entry that '
                'isn\'t yet resolved',
                'example': '2018-10-11T00:00:00Z',

                'type': 'datetime',
                'nullable': True,
                'default': None,
            }
        }
    }
}
