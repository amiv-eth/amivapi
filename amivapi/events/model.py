# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event resource settings.

Contains mode and function to create schema.
As soon as we switch to mongo this will only have the schema.
"""

from amivapi.settings import EMAIL_REGEX
from .authorization import EventAuth, EventSignupAuth


description_events = ("""
An event is anything happening within the organization you want others to know
of and join.

<br />

## Moderator

Events can have a *Moderator*. The Moderator can modify the events, and view
signups for the moderated events.

<br />

## Internationalization

Events support both german and english titles, descriptions and catchphrases.
At least one language is required, but if possible, both english and german
versions should be included.


<br />

## Images

While the API generally accepts both `form-data` and JSON-input,
images can only be sent using [`multipart/form-data`][1]. There's a quick
how-to on sending data in the [cheatsheet](#section/Cheatsheet/Sending-Data).

[1]: https://www.w3.org/TR/html5/sec-forms.html#multipart-form-data


<br />

## Signups

Events can require signup by setting the `spots` field to a numerical value,
from `0` for unlimited spots for participants to `n` for `n` spots.
If signup is enabled (i.e. if `spots` is not Null),
[Eventsignups](#tag/Eventsignup) can be created.


### Public Signup

Usually, only [Users](#tag/User) will be able to sign up for events. However,
by setting `allow_email_signup`, the event can be made *public*, allowing
signup with only an email address.


### Signup Selection

Eventsignups can be accepted or not (waiting list) and you can control the
acceptance of signups with the `selection_strategy` field.
Currently, the following strategies are supported:

<table>
  <tr>
    <th>Strategy</th>
    <th>Description</th>
  </tr>
    <td><b>fcfs</b></td>
    <td>
      <em>First come, first serve</em>. Signups are accepted as long as
      spots are available. If an accepted signup gets deleted, the most
      recent unaccepted signup will be accepted automatically.
    </td
  </tr>
  <tr>
    <td><b>manual</b></td>
    <td>
      All signups have to be accepted by an admin manually.
    </td
  </tr>
</table>


### Additional Fields

Often, events require additional information from participants, e.g. whether
they posses a train ticket or which kind of food they prefer.

With `additional_field`, the API provides a flexible way to specify such
requirements using [JSON Schemas](https://json-schema.org):

1. The event includes a JSON schema in `additional_fields`.
2. Each signup sends `additional_fields` as well, which will be validated
   using the schema provided by the event.

In both cases, a JSON Object must be passed as a string. (In JavaScript, an
object can be turned into a string using `JSON.stringify`. The python
equivalent is `json.dumps`)

For example, the following `additional_field`-schema asks users to select
their SBB Abo and marks this field as *required*, i.e. it may not be left
blank (Remember to send this object as a string, as explained above).

```
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "additionalProperties": false,
    "type": "object",
    "properties": {
        "SBB_Abo": {
            "type": "string",
            "enum": ["None", "GA", "Halbtax", "Gleis 7"],
        },
    "required": ["SBB_Abo"]
}
```

> Currently, we only support JSON Schema
> [Draft 4](https://json-schema.org/specification-links.html#draft-4) and
> additionally require `additionalProperties` to be `false`.

An event can now provide the following object (again, as a string) with the
signup:

```
{
    "SBB_Abo": "GA"
}
```
""")

description_signups = ("""
A signup to an [Event](#tag/Event).
""")

eventdomain = {
    'events': {
        'description': description_events,

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': EventAuth,

        'public_methods': ['GET', 'HEAD'],
        'public_item_methods': ['GET', 'HEAD'],

        'schema': {
            'title_de': {
                'title': 'German Title',
                'description': 'German title of the event.',
                'example': 'API Vorstellung',

                'nullable': True,
                'default': None,
                'type': 'string',
                'maxlength': 100,
                'dependencies': ['catchphrase_de', 'description_de'],
                'required_if_not': 'title_en',
                'no_html': True,
            },
            'title_en': {
                'title': 'English Title',
                'description': 'English title of the event.',
                'example': 'API Presentation',

                'nullable': True,
                'default': None,
                'type': 'string',
                'maxlength': 100,
                'dependencies': ['catchphrase_en', 'description_en'],
                'required_if_not': 'title_de',
                'no_html': True,
            },
            'catchphrase_de': {
                'title': 'German Catchphrase',
                'description': 'Short, memorizable catchphrase in german.',
                'example': "Der Programmierer konzentriert ich auf das "
                           "wesentliche, den REST macht die API.",

                'nullable': True,
                'default': None,
                'type': 'string',
                'maxlength': 500,
                'no_html': True,
            },
            'catchphrase_en': {
                'title': 'English Catchphrase',
                'description': 'Short, memorizable catchphrase in english.',
                'example': "Why did the programmer wake up happy? Because he "
                           "had a RESTful sleep!",

                'nullable': True,
                'default': None,
                'type': 'string',
                'maxlength': 500,
                'no_html': True,
            },
            'description_de': {
                'title': 'German Description',
                'description': 'German (complete) description of the event. '
                               'Does *not* need to include price, location, '
                               'etc., for which dedicated fields exist. '
                               'You can use markdown to style your text, '
                               "but don't use additional html tags.",
                'example': 'Heute abend präsentieren wir die neue API! ...',

                'nullable': True,
                'default': None,
                'type': 'string',
                'maxlength': 10000,
                'no_html': True,
            },
            'description_en': {
                'title': 'English Description',
                'description': 'English (complete) description of the event. '
                               'Does *not* need to include price, location, '
                               'etc., for which dedicated fields exist.'
                               'You can use markdown to style your text, '
                               "but don't use additional html tags.",
                'example': 'Tonight, the new API is unveiled! ...',

                'nullable': True,
                'default': None,
                'type': 'string',
                'maxlength': 10000,
                'no_html': True,
            },
            'location': {
                'description': 'Where the event will take place.',
                'example': 'ETH HG F 30 (Audimax)',

                'maxlength': 50,
                'nullable': True,
                'default': None,
                'type': 'string',
                'no_html': True,
            },
            'price': {
                'description': 'Price in *Rappen*, e.g. '
                               '1000 for 10 CHF.',
                'example': None,

                'min': 1,
                'nullable': True,
                'default': None,
                'type': 'integer',
            },
            'time_start': {
                'title': 'Start',
                'description': 'Start time of the event itself. If you define '
                               'a start time, an end time is required, too.',
                'example': '2018-10-17T18:00:00Z',

                'type': 'datetime',
                'nullable': True,
                'default': None,
                'dependencies': ['time_end'],
                'earlier_than': 'time_end',
            },
            'time_end': {
                'title': 'End',
                'description': 'End time of the event itself. If you define '
                               'an end time, a start time is required, too.',
                'example': '2018-10-17T22:00:00Z',

                'type': 'datetime',
                'nullable': True,
                'default': None,
                'dependencies': ['time_start'],
                'later_than': 'time_start',
            },

            # Images

            'img_infoscreen': {
                'title': 'Infoscreen Image',
                'description': 'Event advertisement image to display on the '
                               'infoscreen. Must have an aspect ratio of '
                               '16:9 (width:height). (`.jpeg` or `.png`)',

                'filetype': ['png', 'jpeg'],
                'type': 'media',
                'aspect_ratio': (16, 9),
                'nullable': True,
                'default': None,
            },
            'img_poster': {
                'title': 'Poster',
                'description': 'Event advertisement image for printed posters.'
                               'Must have an aspect_ratio of 1:1.41 '
                               '(width:height), i.e. the DIN A aspect ratio. '
                               '(`.jpeg` or `.png`)',

                'filetype': ['png', 'jpeg'],
                'type': 'media',
                'nullable': True,
                'default': None,
                'aspect_ratio': (1, 1.41),  # DIN A aspect ratio
            },
            'img_thumbnail': {
                'title': 'Thumbnail',
                'description': 'Event advertisement image thumbnail, e.g. '
                               'for preview and newsletter. Must have an '
                               'aspect ratio of 1:1. (`.jpeg` or `.png`)',
                'filetype': ['png', 'jpeg'],
                'type': 'media',
                'aspect_ratio': (1, 1),
                'nullable': True,
                'default': None,
            },

            # Display settings

            'time_advertising_start': {
                'title': 'Advertisement Start',
                'description': 'Start time of the event advertisement, e.g. '
                               'on the website.',
                'example': '2018-10-10T12:00:00Z',

                'type': 'datetime',
                'required': True,
                'nullable': False,
                'earlier_than': 'time_advertising_end',
            },
            'time_advertising_end': {
                'title': 'Advertisement End',
                'description': 'End time of the event advertisement, e.g. '
                               'on the website.',
                'example': '2018-10-16T18:00:00Z',

                'type': 'datetime',
                'required': True,
                'nullable': False,
                'later_than': 'time_advertising_start'
            },
            'priority': {
                'title': 'Advertisement Priority',
                'description': 'Priority of the event advertisement. Clients '
                               'can use the priority for sorting etc.',
                'example': 3,

                'type': 'integer',
                'min': 0,
                'max': 10,
                'default': 5
            },

            'show_announce': {
                'title': 'Show in Newsletter',
                'description': 'Advertisement of the event in the email '
                               'newsletter or not.',

                'nullable': False,
                'type': 'boolean',
                'default': False,
            },
            'show_infoscreen': {
                'title': 'Show on Infoscreen',
                'description': 'Advertisement of the event on the infoscreen '
                               'or not.',

                'nullable': False,
                'type': 'boolean',
                'default': False,
            },
            'show_website': {
                'title': 'Show on Website',
                'description': 'Advertisement of the event on the website '
                               'or not.',

                'nullable': False,
                'type': 'boolean',
                'default': False,
            },

            # Signups

            'spots': {
                'title': 'Signup Spots',
                'description': "How many spots are available for signup. "
                               "For no signup, set to `Null`. For signup with "
                               "unlimited spots, set to `0`. Otherwise just "
                               "provide number of spots. If signup is "
                               "required, you will need to set signup times "
                               "and a selection strategy, too.",
                'example': 20,

                # Dependencies only for fields without useful defaults
                'dependencies': ['time_register_start',
                                 'time_register_end'],
                'min': 0,
                'nullable': True,
                'default': None,
                'type': 'integer',
            },
            'time_register_start': {
                'title': 'Registration Start',
                'description': 'Start of the registration window.',
                'example': '2018-10-11T18:00:00Z',

                'type': 'datetime',
                'nullable': True,
                'default': None,
                'dependencies': ['time_register_end'],
                'earlier_than': 'time_register_end',
                'only_if_not_null': 'spots'
            },
            'time_register_end': {
                'title': 'Registration End',
                'description': 'End of the registration window.',
                'example': '2018-10-13T17:00:00Z',

                'type': 'datetime',
                'default': None,
                'nullable': True,
                'dependencies': ['time_register_start'],
                'later_than': 'time_register_start',
                'only_if_not_null': 'spots'
            },
            'additional_fields': {
                "description": "JSON schema specifying additional information "
                               "which is required to sign up, e.g. about food "
                               "preferences.",
                "example": None,

                'nullable': True,
                'default': None,
                'type': 'string',
                'json_schema': True,
                'only_if_not_null': 'spots',
            },

            # `allow_email_signup` and `selection` strategy do not depend
            # on `spots` explicitly, because otherwise we cannot set their
            # default values (as they are non None)

            'allow_email_signup': {
                'title': 'Email Signup',
                'description': 'Allow signup without a user account.',

                'nullable': False,
                'default': False,
                'type': 'boolean',
            },

            'selection_strategy': {
                'description': 'Strategy how signups will be accepted, see '
                               'Event resource introduction above for more '
                               'info.',

                'type': 'string',
                'allowed': ['fcfs', 'manual'],
                'default': 'fcfs',
            },

            'signup_count': {
                'description': 'Current number of accepted singups.',

                'readonly': True,
                'type': 'integer'
            },

            'unaccepted_count': {
                'description': 'Current number of unaccepted singups. This may'
                               ' either be participants on the waiting list '
                               'or unconfirmed email signups.',

                'readonly': True,
                'type': 'integer'
            },
            'moderator': {
                'description': '`_id` of a user which will be the event '
                               'moderator, who can modify the event.',
                'example': 'ed1ac3fa99034762f7b55e5a',

                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                },
                'nullable': True,
                'default': None,
            },
        },
    },

    'eventsignups': {
        'resource_title': 'Event Signups',
        'item_title': 'Event Signup',

        'description': description_signups,

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': EventSignupAuth,

        'public_methods': ['POST'],

        'schema': {
            'event': {
                'description': "The event to sign up to (must require "
                               "signup). Cannot be modified with PATCH.",
                'example': "10d8e50e303049ecb856ae9b",

                'data_relation': {
                    'resource': 'events',
                    'embeddable': True,
                    'cascade_delete': True,
                },
                'not_patchable': True,
                'required': True,
                'signup_requirements': True,
                'type': 'objectid',
            },
            'user': {
                "description": "The user to sign up the the event. "
                               "Cannot be modified with PATCH.",
                "example": "5bd19211d57724603b489882",

                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                    'cascade_delete': True,
                },
                'not_patchable': True,
                'only_self_enrollment_for_event': True,
                'not_blacklisted': True,
                'type': 'objectid',
                'nullable': False,
                'unique_combination': ['event'],
                'required': True,
                'excludes': 'email',
            },
            'additional_fields': {
                "description": "Additional signup information, must match the "
                               "schema defined in `additional_fields` of the "
                               "event.",
                "example": None,

                'nullable': True,
                'default': None,
                'type': 'string',
                'json_event_field': True,
            },
            'email': {
                "description": "If a user is signed up, this field is "
                               "read-only and shows the user's email. If the "
                               "event is *public*, this field can be used "
                               "*instead* of the `user` field to sign up "
                               "an unregistered person via email. "
                               "Cannot be modified with PATCH.",
                "example": None,

                'email_signup_must_be_allowed': True,
                'no_user_mail': True,
                'maxlength': 100,
                'not_patchable': True,
                'nullable': False,
                'regex': EMAIL_REGEX,
                'type': 'string',
                'unique_combination': ['event'],
                'required': True,
                'excludes': 'user',
            },
            'confirmed': {
                'description': 'Whether the signup email was confirmed. '
                               '(Only relevant for email signup to public '
                               'events, registered users are automatically '
                               'confirmed)',
                'example': True,

                'type': 'boolean',
                'readonly': True
            },
            'accepted': {
                'description': 'Whether the signup was accepted. If `False`, '
                               'the signup is on the waiting list. Can only '
                               'be modified by the API itself or admins.',
                'example': True,

                'type': 'boolean',
                'admin_only': True,
                'default': False,
            },
            'checked_in': {
                'description': "For some events, it might be useful to track "
                               "who is currently attending, i.e. is checked "
                               "in. `Null` means that the attendance is not "
                               "checked.",

                'default': None,
                'nullable': True,
                'type': 'boolean',
                'admin_only': True
            },
        }
    }
}
