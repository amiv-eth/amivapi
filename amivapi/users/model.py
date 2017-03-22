# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module."""

from amivapi.settings import EMAIL_REGEX

from .security import UserAuth

userdomain = {
    'users': {
        'description': 'User data will be generated from LDAP-data wherever '
                       'possible. Users themselves can modify password, email, '
                       'rfid, phone and send_newsletter. Everything else can '
                       'be changed by admins. The password is optional for '
                       'users with an LDAP entry. When querying users without '
                       'admin permissions, AMIV members can see some metadata '
                       'about other members. External people can see nothing.',
        'additional_lookup': {'field': 'nethz',
                              'url': 'regex(".*[\\w].*")'},

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': UserAuth,

        'schema': {
            'nethz': {
                'type': 'string',
                'empty': False,
                'nullable': True,
                'maxlength': 30,
                'not_patchable_unless_admin': True,
                'unique': True,
                'default': None,  # Do multiple none values work?
                'description': 'Nethz(short ETH name)  of the user. Used for '
                'identification in LDAP and for login.'
            },
            'firstname': {
                'type': 'string',
                'maxlength': 50,
                'empty': False,
                'nullable': False,
                'not_patchable_unless_admin': True,
                'required': True},
            'lastname': {
                'type': 'string',
                'maxlength': 50,
                'empty': False,
                'nullable': False,
                'not_patchable_unless_admin': True,
                'required': True},
            'membership': {
                'allowed': ["none", "regular", "extraordinary", "honorary"],
                'maxlength': 13,
                'not_patchable_unless_admin': True,
                'required': True,
                'type': 'string',
                'unique': False},

            # Values only imported by ldap
            'legi': {
                'maxlength': 8,
                'not_patchable_unless_admin': True,
                'nullable': True,
                'required': False,
                'type': 'string',
                'unique': True
            },
            'department': {
                'type': 'string',
                'allowed': ['itet', 'mavt'],
                'not_patchable_unless_admin': True,
                'nullable': True
            },
            'gender': {
                'type': 'string',
                'allowed': ['male', 'female'],
                'maxlength': 6,
                'not_patchable_unless_admin': True,
                'required': True,
                'unique': False
            },

            # Fields the user can modify himself
            'password': {
                'type': 'string',
                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None,
                'description': 'Leave empty to use just LDAP authentification. '
                'People without LDAP should use this field.'
            },
            'email': {
                'type': 'string',
                'maxlength': 100,
                'regex': EMAIL_REGEX,
                'required': True,
                'unique': True
            },
            'rfid': {
                'type': 'string',
                'maxlength': 6,
                'empty': False,
                'nullable': True,
                'unique': True,
                'description': 'Number on the back of the legi. This is not in '
                'LDAP, therefore users need to enter it themselves to use the '
                'vending machines.'
            },
            'phone': {
                'type': 'string',
                'maxlength': 20,
                'empty': False,
                'nullable': True
            },
            'send_newsletter': {
                'type': 'boolean',
                'nullable': True
            },
        }
    }
}
