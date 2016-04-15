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
from amivapi.utils import Base, make_domain, register_domain, EMAIL_REGEX


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
        return PASSWORD_CONTEXT.encrypt(plaintext)

    def verify_password(self, plaintext):
        """Hash password everytime it changes."""
        is_valid = PASSWORD_CONTEXT.verify(plaintext, self.password)
        if is_valid and PASSWORD_CONTEXT.needs_update(self.password):
            # rehash password
            self.password = plaintext

        return is_valid


def make_userdomain():
    """Create domain.

    This is a function so it can be called after models in all modules have
    been defined.
    """
    userdomain = make_domain(User)

    userdomain['users']['schema']['email'].update(
        {'regex': EMAIL_REGEX})

    # /users
    # Not patchable fields
    for field in ['firstname', 'lastname', 'legi', 'nethz', 'department',
                  'phone', 'gender', 'membership']:
        userdomain['users']['schema'][field].update(
            {'not_patchable_unless_admin': True})

    # Hide passwords
    userdomain['users']['datasource']['projection']['password'] = 0

    # TODO: enums of sqlalchemy should directly be caught by the validator
    userdomain['users']['schema']['gender'].update({
        'allowed': ['male', 'female']
    })
    userdomain['users']['schema']['department'].update({
        'allowed': ['itet', 'mavt'],
    })
    userdomain['users']['schema']['nethz'].update({
        'empty': False,
    })

    # Make it possible to retrive a user with his nethz (/users/nethz)
    userdomain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'nethz',
        }
    })

    return userdomain


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_userdomain())
