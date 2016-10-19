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
        'description': {
            'fields': {
                'additional_fields':
                'must be provided in form of a JSON-Schema. You can add here '
                'fields you want to know from people signing up going further '
                'than their email-address',
                'allow_email_signup': 'If False, only AMIV-Members can sign '
                'up for this event',
                'price': 'Price of the event as Integer in Rappen.',
                'spots': "For no limit, set to '0'. If no signup required, "
                "set to '-1'. Otherwise just provide an integer."
            },
            'general': 'An Event is basically everything happening in the '
            'AMIV. All time fields have the format YYYY-MM-DDThh:mmZ, e.g. '
            '2014-12-20T11:50:06Z',
            'methods': {
                'GET': 'You are always allowed, even without session, '
                'to view AMIV-Events'
            }
        },

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'public_methods': ['GET'],
        'public_item_methods': ['GET'],

        'schema': {
            'title_de': {
                'nullable': True,
                'type': 'string',
                'maxlength': 100,
                'dependencies': ['catchphrase_de', 'description_de']
            },
            'title_en': {
                'nullable': True,
                'type': 'string',
                'maxlength': 100,
                'dependencies': ['catchphrase_en', 'description_en']
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
                'type': 'integer'
            },
            'time_start': {
                'nullable': True,
                'type': 'datetime'
            },
            'time_end': {
                'dependencies': ['time_start'],
                'later_than': 'time_start',
                'nullable': True,
                'type': 'datetime'
            },

            # 'img_banner': {
            #     'filetype': ['png', 'jpeg'],
            #     'type': 'media'
            # },
            # 'img_infoscreen': {
            #     'filetype': ['png', 'jpeg'],
            #     'type': 'media'
            # },
            # 'img_poster': {
            #     'filetype': ['png', 'jpeg'],
            #     'type': 'media'
            # },
            # 'img_thumbnail': {
            #     'filetype': ['png', 'jpeg'],
            #     'type': 'media'
            # },

            'show_announce': {
                'nullable': False,
                'type': 'boolean',
                'required': True
            },
            'show_infoscreen': {
                'nullable': False,
                'type': 'boolean',
                'required': True
            },
            'show_website': {
                'nullable': False,
                'type': 'boolean',
                'required': True,

                # This is basically here, because this is a required
                # field. It will make sure there is always either an english
                # or a german title
                'depends_any': ['title_de', 'title_en']
            },

            'spots': {
                'requires_if_not_null': ['time_register_start',
                                         'time_register_end',
                                         'allow_email_signup'],
                'min': 0,
                'required': True,
                'nullable': True,
                'type': 'integer',
            },
            'time_register_start': {
                'nullable': True,
                'type': 'datetime'
            },
            'time_register_end': {
                'dependencies': ['time_register_start'],
                'later_than': 'time_register_start',
                'nullable': True,
                'type': 'datetime'
            },
            'additional_fields': {
                'nullable': True,
                'type': 'json_schema',
                'only_if_not_null': 'spots'
            },
            'allow_email_signup': {
                'nullable': False,
                'type': 'boolean'
            },

            'signup_count': {
                'readonly': True,
                'type': 'integer'
            },
            # 'signups': {
            #     'data_relation': {
            #         'embeddable': True,
            #         'resource': 'eventsignups'
            #     },
            #     'type': 'objectid',
            #     'readonly': True
            # }
        },
    },

    'eventsignups': {
        'description': {
            'fields': {
                'additional_fields': "Data-schema depends on "
                "'additional_fields' from the mapped event. Please provide in "
                "json-format.",
                'email': 'For registered users, this is just a projection of '
                'your general email-address. External users need to provide '
                'their email here.',
                'user': "Provide either user or email."
            },
            'general': 'You can signup here for an existing event inside of '
            'the registration-window. External Users can only sign up to '
            'public events.',
            'methods': {
                'PATCH': 'Only additional_fields can be changed'
            }
        },

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
                'unique_combination': ['user',
                                       'email'],
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

                # This creates a presence XOR with email
                # TODO: This needs cerberus > 1.0.1
                # enable as soon as eve supports it
                # 'required': True,
                # 'excludes': ['email']
            },
            'additional_fields': {
                'nullable': True,
                'type': 'json_event_field'
            },
            'email': {
                'email_signup_must_be_allowed': True,
                'maxlength': 100,
                'not_patchable': True,
                'nullable': False,
                'regex': EMAIL_REGEX,
                'type': 'string',

                # This creates a presence XOR with user
                # TODO: This needs cerberus > 1.0.1
                # enable as soon as eve supports it
                # 'required': True,
                # 'excludes': ['user']
            },
            'confirmed': {
                'nullable': True,
                'type': 'boolean',
                'readonly': True
            },
        }
    }
}
