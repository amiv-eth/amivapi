# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event resource settings.

Contains mode and function to create schema.
As soon as we switch to mongo this will only have the schema.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
    Unicode,
    UnicodeText,
    Text,
    Boolean,
    Integer,
    CHAR)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from amivapi import utils


class Event(utils.Base):
    """Event model."""

    __description__ = {
        'general': "An Event is basically everything happening in the AMIV. "
        "All time fields have the format YYYY-MM-DDThh:mmZ, e.g. "
        "2014-12-20T11:50:06Z",
        'methods': {
            'GET': "You are always allowed, even without session, to view "
            "AMIV-Events"
        },
        'fields': {
            'price': 'Price of the event as Integer in Rappen.',
            'additional_fields': "must be provided in form of a JSON-Schema. "
            "You can add here fields you want to know from people signing up "
            "going further than their email-address",
            'allow_email_signup': "If False, only AMIV-Members can sign up "
            "for this event",
            'spots': "For no limit, set to '0'. If no signup required, set to "
            "'-1'. Otherwise just provide an integer.",
        }
    }
    __expose__ = True
    __projected_fields__ = ['signups']

    __public_methods__ = ['GET']

    time_start = Column(DateTime)
    time_end = Column(DateTime)
    location = Column(Unicode(50))
    allow_email_signup = Column(Boolean, default=False, nullable=False)
    price = Column(Integer)  # Price in Rappen
    spots = Column(Integer, nullable=False)
    time_register_start = Column(DateTime)
    time_register_end = Column(DateTime)
    additional_fields = Column(Text)
    show_infoscreen = Column(Boolean, default=False)
    show_website = Column(Boolean, default=False)
    show_announce = Column(Boolean, default=False)

    @hybrid_property
    def signup_count(self):
        """Get number of signups."""
        return len(self.signups)

    # Images
    img_thumbnail = Column(CHAR(100))
    img_banner = Column(CHAR(100))
    img_poster = Column(CHAR(100))
    img_infoscreen = Column(CHAR(100))

    title_de = Column(UnicodeText)
    title_en = Column(UnicodeText)
    description_de = Column(UnicodeText)
    description_en = Column(UnicodeText)
    catchphrase_de = Column(UnicodeText)
    catchphrase_en = Column(UnicodeText)

    # relationships
    signups = relationship("EventSignup", backref="event",
                           cascade="all")


class EventSignup(utils.Base):
    """Model for a signup."""

    __description__ = {
        'general': "You can signup here for an existing event inside of the "
        "registration-window. External Users can only sign up to public "
        "events.",
        'fields': {
            'additional_fields': "Data-schema depends on 'additional_fields' "
            "from the mapped event. Please provide in json-format.",
            'user_id': "To sign up as external user, set 'user_id' to '-1'",
            'email': "For registered users, this is just a projection of your "
            "general email-address. External users need to provide their email"
            " here.",
        }}
    __expose__ = True
    __projected_fields__ = ['event', 'user']

    __owner__ = ['user_id']
    __owner_methods__ = ['GET', 'PATCH', 'DELETE']
    __registered_methods__ = ['POST']

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(CHAR(100), ForeignKey("users.email"))
    additional_fields = Column(Text)

    """for unregistered users"""
    _email_unreg = Column(Unicode(100))
    _token = Column(CHAR(20), unique=True, nullable=True)
    _confirmed = Column(Boolean, default=False)



eventdomain = {'events': {'datasource': {'projection': {'_author': 1,
                                          'additional_fields': 1,
                                          'allow_email_signup': 1,
                                          'catchphrase_de': 1,
                                          'catchphrase_en': 1,
                                          'description_de': 1,
                                          'description_en': 1,
                                          'id': 1,
                                          'img_banner': 1,
                                          'img_infoscreen': 1,
                                          'img_poster': 1,
                                          'img_thumbnail': 1,
                                          'location': 1,
                                          'price': 1,
                                          'show_announce': 1,
                                          'show_infoscreen': 1,
                                          'show_website': 1,
                                          'signup_count': 1,
                                          'signups': 1,
                                          'spots': 1,
                                          'time_end': 1,
                                          'time_register_end': 1,
                                          'time_register_start': 1,
                                          'time_start': 1,
                                          'title_de': 1,
                                          'title_en': 1},
                           'source': 'Event'},
            'description': {'fields': {'additional_fields': 'must be provided in form of a JSON-Schema. You can add here fields you want to know from people signing up going further than their email-address',
                                       'allow_email_signup': 'If False, only AMIV-Members can sign up for this event',
                                       'price': 'Price of the event as Integer in Rappen.',
                                       'spots': "For no limit, set to '0'. If no signup required, set to '-1'. Otherwise just provide an integer."},
                            'general': 'An Event is basically everything happening in the AMIV. All time fields have the format YYYY-MM-DDThh:mmZ, e.g. 2014-12-20T11:50:06Z',
                            'methods': {'GET': 'You are always allowed, even without session, to view AMIV-Events'}},
            'embedded_fields': {},
            'item_lookup': True,
            'item_lookup_field': '_id',
            'item_url': 'regex("[0-9]+")',
            'owner': [],
            'owner_methods': [],
            'public_item_methods': ['GET'],
            'public_methods': ['GET'],
            'registered_methods': [],
            'schema': {'_author': {'data_relation': {'resource': 'users'},
                                   'nullable': True,
                                   'readonly': True,
                                   'type': 'objectid'},
                       'additional_fields': {'nullable': True,
                                             'type': 'json_schema'},
                       'allow_email_signup': {'required': True,
                                              'type': 'boolean'},
                       'catchphrase_de': {'nullable': True,
                                          'type': 'string'},
                       'catchphrase_en': {'nullable': True,
                                          'type': 'string'},
                       'description_de': {'nullable': True,
                                          'type': 'string'},
                       'description_en': {'nullable': True,
                                          'type': 'string'},
                       'img_banner': {'filetype': ['png', 'jpeg'],
                                      'type': 'media'},
                       'img_infoscreen': {'filetype': ['png', 'jpeg'],
                                          'type': 'media'},
                       'img_poster': {'filetype': ['png', 'jpeg'],
                                      'type': 'media'},
                       'img_thumbnail': {'filetype': ['png', 'jpeg'],
                                         'type': 'media'},
                       'location': {'maxlength': 50,
                                    'nullable': True,
                                    'type': 'string'},
                       'price': {'min': 0,
                                 'nullable': True,
                                 'type': 'integer'},
                       'show_announce': {'nullable': True,
                                         'type': 'boolean'},
                       'show_infoscreen': {'nullable': True,
                                           'type': 'boolean'},
                       'show_website': {'nullable': True,
                                        'type': 'boolean'},
                       'signup_count': {'readonly': True,
                                        'type': 'string'},
                       'signups': {'data_relation': {'embeddable': True,
                                                     'resource': 'eventsignups'},
                                   'type': 'objectid'},
                       'spots': {'if_this_then': ['time_register_start',
                                                  'time_register_end'],
                                 'min': -1,
                                 'required': True,
                                 'type': 'integer'},
                       'time_end': {'dependencies': ['time_start'],
                                    'later_than': 'time_start',
                                    'nullable': True,
                                    'type': 'datetime'},
                       'time_register_end': {'dependencies': ['time_register_start'],
                                             'later_than': 'time_register_start',
                                             'nullable': True,
                                             'type': 'datetime'},
                       'time_register_start': {'nullable': True,
                                               'type': 'datetime'},
                       'time_start': {'nullable': True,
                                      'type': 'datetime'},
                       'title_de': {'nullable': True,
                                    'type': 'string'},
                       'title_en': {'nullable': True,
                                    'type': 'string'}},
            'sql_model': Event},
 'eventsignups': {'datasource': {'projection': {'_author': 1,
                                                '_confirmed': 1,
                                                '_email_unreg': 1,
                                                '_token': 1,
                                                'additional_fields': 1,
                                                'email': 1,
                                                'event': 1,
                                                'event_id': 1,
                                                'id': 1,
                                                'user': 1,
                                                'user_id': 1},
                                 'source': 'EventSignup'},
                  'description': {'fields': {'additional_fields': "Data-schema depends on 'additional_fields' from the mapped event. Please provide in json-format.",
                                             'email': 'For registered users, this is just a projection of your general email-address. External users need to provide their email here.',
                                             'user_id': "To sign up as external user, set 'user_id' to '-1'"},
                                  'general': 'You can signup here for an existing event inside of the registration-window. External Users can only sign up to public events.'},
                  'embedded_fields': {},
                  'item_lookup': True,
                  'item_lookup_field': '_id',
                  'item_url': 'regex("[0-9]+")',
                  'owner': ['user_id'],
                  'owner_methods': ['GET', 'PATCH', 'DELETE'],
                  'public_item_methods': [],
                  'public_methods': [],
                  'registered_methods': ['POST'],
                  'resource_methods': ['GET'],
                  'schema': {'_author': {'data_relation': {'resource': 'users'},
                                         'nullable': True,
                                         'readonly': True,
                                         'type': 'objectid'},
                             '_confirmed': {'nullable': True,
                                            'type': 'boolean'},
                             'additional_fields': {'nullable': True,
                                                   'type': 'json_event_field'},
                             'email': {'email_signup_must_be_allowed': True,
                                       'maxlength': 100,
                                       'not_patchable': True,
                                       'nullable': True,
                                       'only_anonymous': True,
                                       'regex': '^.+@.+$',
                                       'type': 'objectid',
                                       'unique_combination': ['event_id']},
                             'event': {'data_relation': {'embeddable': True,
                                                         'resource': 'events'},
                                       'type': 'objectid'},
                             'event_id': {'data_relation': {'resource': 'events'},
                                          'not_patchable': True,
                                          'required': True,
                                          'signup_requirements': True,
                                          'type': 'objectid',
                                          'unique_combination': ['user_id',
                                                                 'email']},
                             'user_id': {'data_relation': {'resource': 'users'},
                                         'not_patchable': True,
                                         'only_self_enrollment_for_event': True,
                                         'required': True,
                                         'type': 'objectid',
                                         'unique_combination': ['event_id']}},
                  'sql_model': EventSignup}}
