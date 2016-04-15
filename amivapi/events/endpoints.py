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


def make_eventdomain():
    """Create domain.

    This is a function so it can be called after models in all modules have
    been defined.
    """
    eventdomain = {}

    eventdomain.update(utils.make_domain(Event))
    eventdomain.update(utils.make_domain(EventSignup))

    # additional validation
    eventdomain['events']['schema']['additional_fields'].update({
        'type': 'json_schema'})
    eventdomain['events']['schema']['price'].update({'min': 0})
    eventdomain['events']['schema']['spots'].update({
        'min': -1,
        'if_this_then': ['time_register_start', 'time_register_end']})
    eventdomain['events']['schema']['time_register_end'].update({
        'dependencies': ['time_register_start'],
        'later_than': 'time_register_start'})
    eventdomain['events']['schema']['time_end'].update({
        'dependencies': ['time_start'],
        'later_than': 'time_start'})

    # time_end for /events requires time_start
    eventdomain['events']['schema']['time_end'].update({
        'dependencies': ['time_start']
    })

    # event images
    eventdomain['events']['schema'].update({
        'img_thumbnail': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_banner': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_poster': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_infoscreen': {'type': 'media', 'filetype': ['png', 'jpeg']}
    })

    # POST done by custom endpoint
    eventdomain['eventsignups']['resource_methods'] = ['GET']

    # schema extensions including custom validation
    eventdomain['eventsignups']['schema']['event_id'].update({
        'not_patchable': True,
        'unique_combination': ['user_id', 'email'],
        'signup_requirements': True})
    eventdomain['eventsignups']['schema']['user_id'].update({
        'not_patchable': True,
        'unique_combination': ['event_id'],
        'only_self_enrollment_for_event': True})
    eventdomain['eventsignups']['schema']['email'].update({
        'not_patchable': True,
        'unique_combination': ['event_id'],
        'only_anonymous': True,
        'email_signup_must_be_allowed': True,
        'regex': utils.EMAIL_REGEX})

    # Since the data relation is not evaluated for posting, we need to remove
    # it from the schema TODO: EXPLAIN BETTER
    del(eventdomain['eventsignups']['schema']['email']['data_relation'])
    # Remove _email_unreg and _token from the schema since they are only
    # for internal use and should not be visible
    del(eventdomain['eventsignups']['schema']['_email_unreg'])
    del(eventdomain['eventsignups']['schema']['_token'])

    eventdomain['eventsignups']['schema']['additional_fields'].update({
        'type': 'json_event_field'})

    return eventdomain
