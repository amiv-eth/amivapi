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



class File(Base):
    """This is a file that belongs to a study document.

    An additional name for the file is possible
    A studydocument needs to be referenced

    Files can only be created and deleted (or both, put), patching them is not
    intended
    """

    __expose__ = True

    __owner__ = ['_author']  # This permitts everybody to post here!
    __owner_methods__ = ['GET', 'PUT', 'DELETE']
    __registered_methods__ = ['GET']

    name = Column(Unicode(100))
    data = Column(CHAR(100))  # This will be modified in schemas.py!
    study_doc_id = Column(Integer, ForeignKey("studydocuments.id"),
                          nullable=False)


class StudyDocument(Base):
    __description__ = {
        'general': "Study-documents are basically all documents that are "
        "connected to a course. This resource provides meta-data for the "
        "assigned files.",
        'fields': {
            'semester': "Study-Semester as an Integer starting with first "
            "semester Bachelor."
        }
    }
    __expose__ = True
    __projected_fields__ = ['files']

    __owner__ = ['_author']
    __owner_methods__ = ['GET', 'PUT', 'PATCH', 'DELETE']
    __registered_methods__ = ['GET', 'POST']

    name = Column(Unicode(100))
    type = Column(String(30))
    exam_session = Column(String(10))
    department = Column(Enum("itet", "mavt"))
    lecture = Column(Unicode(100))
    professor = Column(Unicode(100))
    semester = Column(Integer)
    author_name = Column(Unicode(100))

    # relationships
    files = relationship("File", backref="study_doc",
                         cascade="all")


class Purchase(Base):
    __description__ = {
        'general': "A beer machine or kaffi machine transaction. Users should"
        " be able to get beer or kaffi, if their last timestamp is older than"
        " one day and they are AMIV members. This resource is used to log"
        " their purchases.",
        'fields': {
            'slot': "Slot in the machine which was purchased(different items,"
            " which may have different prices)."
        }
    }
    __expose__ = True

    __owner__ = ['user_id']
    __owner_methods__ = ['GET']

    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime)
    type = Column(Enum("beer", "kaffi"))
    slot = Column(Integer)
