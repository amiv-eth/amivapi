# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module."""

from datetime import timedelta
from textwrap import dedent

from amivapi.settings import EMAIL_REGEX

from .security import UserAuth

description = dedent("""
Users are people that may or may not be AMIV members.

<br />

## Synchronization with ETHZ

User data is synchronized with the ETH directory server in two ways:

1. The API periodically updates all members of the organization

2. Whenever you log in, you user data is imported, even if you are not a
   member

Concretely, the following fields are synchronized:

- `nethz`
- `firstname`
- `lastname`
- `membership`
- `legi`
- `department`
- `gender`

<br />

## Security

In addition to the usual
[permissions](#section/Authentication-and-Authorization/Authorization),
some further constraints are in place:

- Passwords are salted and hashed, and they are *never* returned by the API,
  not even to admins. Furthermore, showing passwords can not be forced
  by projections.

- **Users** can only view all of their own fields only.
  For other users, only `firstname`, `lastname` and `nethz` are visible.

- **Admins** can view the complete fields for all users.

- All fields synchronized with ETHZ (see above) *cannot be modified* by users.
""")


userdomain = {
    'users': {
        'description': description,
        'additional_lookup': {'field': 'nethz',
                              'url': 'string'},

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': UserAuth,

        'mongo_indexes': {
            'legi': ([('legi', 1)], {'background': True}),
            'nethz': ([('nethz', 1)], {'background': True}),
            'firstname': ([('firstname', 1)], {'background': True}),
            'lastname': ([('lastname', 1)], {'background': True}),
            'email': ([('email', 1)], {'background': True})
        },

        'schema': {
            'nethz': {
                'type': 'string',
                'empty': False,
                'nullable': True,
                'maxlength': 30,
                'not_patchable_unless_admin': True,
                'unique': True,
                'default': None,
                'no_html': True,

                'title': 'n.ethz',
                'description': 'n.ethz (ETHZ shortname) of the user. Used for '
                               'identification and login.',
                'example': "pablop",
            },
            'firstname': {
                'type': 'string',
                'maxlength': 50,
                'empty': False,
                'nullable': False,
                'not_patchable_unless_admin': True,
                'required': True,
                'no_html': True,
                'example': 'Pablo',
            },
            'lastname': {
                'type': 'string',
                'maxlength': 50,
                'empty': False,
                'nullable': False,
                'not_patchable_unless_admin': True,
                'required': True,
                'no_html': True,
                'example': 'Pablone',
            },
            'membership': {
                'allowed': ["none", "regular", "extraordinary", "honorary"],
                'not_patchable_unless_admin': True,
                'required': True,
                'type': 'string',
                'unique': False,
                'example': 'regular',
            },

            # Values only imported by ldap
            'legi': {
                'maxlength': 8,
                'not_patchable_unless_admin': True,
                'nullable': True,
                'required': False,
                'type': 'string',
                'unique': True,
                'no_html': True,
                'description': 'ETHZ legi card number',
                'example': "18917412",
            },
            'department': {
                'type': 'string',
                'allowed': ['itet', 'mavt'],
                'not_patchable_unless_admin': True,
                'nullable': True,
                'default': None,
                'example': 'itet'
            },
            'gender': {
                'type': 'string',
                'allowed': ['male', 'female'],
                'not_patchable_unless_admin': True,
                'required': True,
                'example': 'male',
            },

            # Fields the user can modify himself
            'password': {
                'type': 'string',
                'minlength': 7,
                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None,
                'description': 'Leave empty to use just LDAP authentification. '
                'People without LDAP should use this field.',
                'session_younger_than': timedelta(minutes=1),
                'example': "Hunter2",
                'writeonly': True,  # 'writeonly' only affects the docs
            },
            'email': {
                'type': 'string',
                'maxlength': 100,
                'regex': EMAIL_REGEX,
                'required': True,
                'unique': True,
                'example': "pablop@ethz.ch"
            },
            'rfid': {
                'type': 'string',
                'maxlength': 6,
                'empty': False,
                'nullable': True,
                'default': None,
                'unique': True,

                'title': 'RFID',
                'description': 'Number on the back of the legi. Contrary to'
                               'the legi number, this information cannot be '
                               'synchronized with ETHZ and has to be entered '
                               'manually.',
                'no_html': True
            },
            'phone': {
                'type': 'string',
                'maxlength': 20,
                'empty': False,
                'nullable': True,
                'default': None,
                'no_html': True,

                'title': 'Phone Number',
                'example': '+41 12 345 67 89'
            },
            'send_newsletter': {
                'type': 'boolean',
                'default': False,

                'title': 'Newletter Subscription',
                'description': 'Flag indicating if the user is subscribed '
                               'to the newsletter.',
                'example': 'True',
            },
            'password_set': {
                'type': 'boolean',
                'description': 'True if a password is set. False if '
                'authentication is only possible via ETHZ.',
                'readonly': True,
                'example': 'False',
            }
        }
    }
}
