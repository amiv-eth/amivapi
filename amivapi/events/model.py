# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event resource settings.

Contains mode and function to create schema.
As soon as we switch to mongo this will only have the schema.
"""

from amivapi.settings import EMAIL_REGEX
from .authorization import EventSignupAuth


eventdomain = {
    'events': {
        'description': 'An Event is basically everything happening in the '
        'AMIV. All time fields have the format YYYY-MM-DDThh:mmZ, e.g. '
        '2014-12-20T11:50:06Z\n\n'
        'GET: This is public even without a session',

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'public_methods': ['GET'],
        'public_item_methods': ['GET'],

        'schema': {
            'title_de': {
                'nullable': True,
                'type': 'string',
                'maxlength': 100,
                'dependencies': ['catchphrase_de', 'description_de'],
                'required_if_not': 'title_en'
            },
            'title_en': {
                'nullable': True,
                'type': 'string',
                'maxlength': 100,
                'dependencies': ['catchphrase_en', 'description_en'],
                'required_if_not': 'title_de'
            },
            'catchphrase_de': {
                'nullable': True,
                'type': 'string',
                'maxlength': 500
            },
            'catchphrase_en': {
                'nullable': True,
                'type': 'string',
                'maxlength': 500
            },
            'description_de': {
                'nullable': True,
                'type': 'string',
                'maxlength': 10000
            },
            'description_en': {
                'nullable': True,
                'type': 'string',
                'maxlength': 10000
            },
            'location': {
                'maxlength': 50,
                'nullable': True,
                'type': 'string'
            },
            'price': {
                'min': 0,
                'nullable': True,
                'type': 'integer',
                'description': 'Price of the event as Integer in Rappen.'
            },
            'time_start': {
                'type': 'datetime',
                'nullable': True,
                'dependencies': ['time_end'],
                'earlier_than': 'time_end',
            },
            'time_end': {
                'type': 'datetime',
                'nullable': True,
                'dependencies': ['time_start'],
                'later_than': 'time_start',
            },

            # Images

            'img_banner': {
                'filetype': ['png', 'jpeg'],
                'type': 'media'
            },
            'img_infoscreen': {
                'filetype': ['png', 'jpeg'],
                'type': 'media'
            },
            'img_poster': {
                'filetype': ['png', 'jpeg'],
                'type': 'media'
            },
            'img_thumbnail': {
                'filetype': ['png', 'jpeg'],
                'type': 'media'
            },

            # Display settings

            'time_advertising_start': {
                'type': 'datetime',
                'required': True,
                'nullable': False,
                'earlier_than': 'time_advertising_end',
            },
            'time_advertising_end': {
                'type': 'datetime',
                'required': True,
                'nullable': False,
                'later_than': 'time_advertising_start'
            },
            'priority': {
                'type': 'integer',
                'min': 0,
                'max': 10,
                'required': True,
                'default': 5
            },

            'show_announce': {
                'nullable': False,
                'type': 'boolean',
                'default': False,
            },
            'show_infoscreen': {
                'nullable': False,
                'type': 'boolean',
                'default': False,
            },
            'show_website': {
                'nullable': False,
                'type': 'boolean',
                'default': False,
            },

            # Signups

            'spots': {
                'dependencies': ['time_register_start',
                                 'time_register_end',
                                 'selection_strategy'],
                'min': 0,
                'nullable': True,
                'type': 'integer',
                'description': "For no signup, set to 'null'. Unlimited spots "
                "if set to '0'. Otherwise just provide number of spots."
            },
            'time_register_start': {
                'type': 'datetime',
                'nullable': True,
                'dependencies': ['time_register_end'],
                'earlier_than': 'time_register_end',
                'only_if_not_null': 'spots'
            },
            'time_register_end': {
                'type': 'datetime',
                'nullable': True,
                'dependencies': ['time_register_start'],
                'later_than': 'time_register_start',
                'only_if_not_null': 'spots'
            },
            'additional_fields': {
                'nullable': True,
                'type': 'string',
                'json_schema': True,
                'only_if_not_null': 'spots',
                'description': 'must be provided in form of a JSON-Schema. You'
                'can add here fields you want to know from people signing up '
                'going further than their email-address.\nThe JSON-Schema will'
                ' always require these fields: {'
                '"$schema": "http://json-schema.org/draft-04/schema#",'
                '"type": "object",'
                '"additionalProperties": false}'
            },
            'allow_email_signup': {
                'nullable': False,
                'type': 'boolean',
                'only_if_not_null': 'spots',
                'description': 'If False, only AMIV-Members can sign up for '
                'this event'
            },

            'selection_strategy': {
                'type': 'string',
                'allowed': ['fcfs', 'manual'],
                'only_if_not_null': 'spots'
            },

            'signup_count': {
                'readonly': True,
                'type': 'integer'
            },
        },
    },

    'eventsignups': {
        'description': 'You can signup here for an existing event inside of '
        'the registration-window. External Users can only sign up to public '
        'events.\n\n'
        'PATCH: Only additional fields can be changed.',

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'public_methods': ['POST'],

        'authentication': EventSignupAuth,

        'schema': {
            'event': {
                'data_relation': {
                    'resource': 'events',
                    'embeddable': True
                },
                'not_patchable': True,
                'required': True,
                'signup_requirements': True,
                'type': 'objectid',
            },
            'user': {
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True
                },
                'not_patchable': True,
                'only_self_enrollment_for_event': True,
                'type': 'objectid',
                'nullable': False,
                'unique_combination': ['event'],
                'description': 'Provide either user or email.',

                # This creates a presence XOR with email
                # Cerberus <= 1.2: Causes problems with `None` values, which
                # should be treated as missing fields, which is not yet
                # possible, causing problems if `None` already exists in db
                #'required': True,
                #'excludes': ['email']
            },
            'additional_fields': {
                'nullable': True,
                'type': 'string',
                'json_event_field': True,
                'description': "Data-schema depends on 'additional_fields' "
                "from the mapped event. Please provide in json-format."
            },
            'email': {
                'email_signup_must_be_allowed': True,
                'maxlength': 100,
                'not_patchable': True,
                'nullable': False,
                'regex': EMAIL_REGEX,
                'type': 'string',
                'unique_combination': ['event'],
                'description': 'For registered users, this is just a projection'
                ' of your general email-address. External users need to provide'
                ' their email here.',

                # This creates a presence XOR with user
                # see above
                #'required': True,
                #'excludes': ['user']
            },
            'confirmed': {
                'type': 'boolean',
                'readonly': True
            },
            'accepted': {
                'type': 'boolean',
                'admin_only': True
            },
            'checked_in': {
                'default': None,
                'nullable': True,
                'type': 'boolean',
                'admin_only': True
            },
        }
    }
}
