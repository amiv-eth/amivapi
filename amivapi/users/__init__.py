# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module."""

from sqlalchemy import (
    Column,
    Unicode,
    CHAR,
    String,
    Enum,
    Boolean
)
from sqlalchemy.orm import relationship, validates

from amivapi.settings import PASSWORD_CONTEXT
from amivapi.utils import Base, register_domain, EMAIL_REGEX


class User(Base):
    """User model."""

    __description__ = {
        'general': "In general, the user data will be generated from "
        "LDAP-Data. However, one might change the RFID-Number or the "
        "membership-status. Extraordinary members may not have a LDAP-Account "
        "and can therefore access all given fields.",
        'methods': {
            'GET': "Authorization is required for most of the fields"
        }}
    __expose__ = True
    __projected_fields__ = ['groupmemberships']

    __owner__ = ['id']
    __owner_methods__ = ['GET', 'PATCH']

    password = Column(CHAR(100))  # base64 encoded hash data
    firstname = Column(Unicode(50), nullable=False)
    lastname = Column(Unicode(50), nullable=False)
    legi = Column(CHAR(8), unique=True)
    rfid = Column(CHAR(6), unique=True)
    nethz = Column(String(30), unique=True)
    department = Column(Enum("itet", "mavt", "other"))
    phone = Column(String(20))
    gender = Column(Enum("male", "female"), nullable=False)
    email = Column(CHAR(100), nullable=False, unique=True)
    membership = Column(Enum("none", "regular", "extraordinary", "honorary"),
                        nullable=False, default="none", server_default="none")
    send_newsletter = Column(Boolean, default=True)

    # relationships
    groupmemberships = relationship("GroupMember",
                                    foreign_keys="GroupMember.user_id",
                                    backref="user", cascade="all")
    sessions = relationship("Session", foreign_keys="Session.user_id",
                            backref="user", cascade="all")
    eventsignups = relationship("EventSignup",
                                foreign_keys="EventSignup.user_id",
                                backref="user", cascade="all")

    @validates("password")
    def update_password(self, key, plaintext):
        """Transparently encodes the plaintext password as a salted hash.

        The salt is regenerated each time a new password is set.
        """
        if plaintext is None:
            return None
        else:
            return PASSWORD_CONTEXT.encrypt(plaintext)

    def verify_password(self, plaintext):
        """Check password."""
        is_valid = PASSWORD_CONTEXT.verify(plaintext, self.password)
        if is_valid and PASSWORD_CONTEXT.needs_update(self.password):
            # rehash password
            self.password = plaintext

        return is_valid


userdomain = {
    'users': {
        'description': {'general': 'In general, the user data will be '
                        'generated from LDAP-Data. However, one might change '
                        'the RFID-Number or the membership-status. '
                        'Extraordinary members may not have a LDAP-Account '
                        'and can therefore access all given fields.',
                        'methods': {'GET': 'Authorization is required for '
                                    'most of the fields'}},

        'additional_lookup': {'field': 'nethz',
                              'url': 'regex(".*[\\w].*")'},

        'datasource': {'source': 'User',
                       'projection': {
                           '_author': 1,
                           'department': 1,
                           'email': 1,
                           'eventsignups': 0,
                           'firstname': 1,
                           'gender': 1,
                           'groupmemberships': 1,
                           'id': 1,
                           'lastname': 1,
                           'legi': 1,
                           'membership': 1,
                           'nethz': 1,
                           'password': 0,
                           'phone': 1,
                           'rfid': 1,
                           'send_newsletter': 1,
                           'sessions': 0}
                       },
        'item_lookup': True,
        'item_lookup_field': '_id',
        'item_url': 'regex("[0-9]+")',

        'resource_methods': ['GET', 'POST'],
        'public_item_methods': [],
        'public_methods': [],

        'registered_methods': [],

        'owner': ['id'],
        'owner_methods': ['GET', 'PATCH'],

        'schema': {
            'nethz': {
                'type': 'string',
                'empty': False,
                'nullable': True,
                'maxlength': 30,
                'not_patchable_unless_admin': True,
                'unique': True,
                'default': None},  # Do multiple none values work?
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
                'unique': True},
            'department': {
                'type': 'string',
                'allowed': ['itet', 'mavt'],
                'not_patchable_unless_admin': True,
                'nullable': True},
            'gender': {
                'type': 'string',
                'allowed': ['male', 'female'],
                'maxlength': 6,
                'not_patchable_unless_admin': True,
                'required': True,
                'unique': False},

            # Fields the user can modify himself
            'password': {
                'type': 'string',
                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None},
            'email': {
                'type': 'string',
                'maxlength': 100,
                'regex': EMAIL_REGEX,
                'required': True,
                'unique': True},
            'rfid': {
                'type': 'string',
                'maxlength': 6,
                'empty': False,
                'nullable': True,
                'unique': True},
            'phone': {
                'type': 'string',
                'maxlength': 20,
                'empty': False,
                'nullable': True},
            'send_newsletter': {
                'type': 'boolean',
                'nullable': True},

            # Relationships
            'eventsignups': {
                'data_relation': {'embeddable': True,
                                  'resource': 'eventsignups'},
                'type': 'objectid',
                'readonly': True},
            'groupmemberships': {
                'data_relation': {'embeddable': True,
                                  'resource': 'groupmembers'},
                'type': 'objectid',
                'readonly': True},
            'sessions': {
                'data_relation': {'embeddable': True,
                                  'resource': 'sessions'},
                'type': 'objectid',
                'readonly': True}
        },

        'sql_model': User
    }
}


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, userdomain)
