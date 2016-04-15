# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.


from sqlalchemy import (
    Column,
    Unicode,
    UnicodeText,
    Text,
    CHAR,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Enum,
    Boolean
)
from sqlalchemy.orm import relationship, validates

from amivapi.settings import PASSWORD_CONTEXT
from amivapi.utils import Base


class User(Base):
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
        is_valid = PASSWORD_CONTEXT.verify(plaintext, self.password)
        if is_valid and PASSWORD_CONTEXT.needs_update(self.password):
            # rehash password
            self.password = plaintext

        return is_valid
