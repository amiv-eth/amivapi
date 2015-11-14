# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import datetime as dt

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
    Boolean,
    UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, synonym

#
# Eve exspects the resource names to be equal to the table names. Therefore
# we generate all names from the Class names. Please choose classnames
# carefully, as changing them might break a lot of code
#


class BaseModel(object):
    """Mixin for common columns."""

    # __abstract__ makes SQL Alchemy not create a table for this class
    __abstract__ = True

    # All classes which overwrite this with True will get exposed as a resource
    __expose__ = False

    # For documentation
    __description__ = {}

    # This is a list of fields, which are added to the projection created by
    # eve. Add any additional field to be delivered on GET requests by default
    # in the subclasses.
    __projected_fields__ = []

    # These can contain a list of methods which need some kind of
    # authorization. If nothing is set only admins can access the method
    __public_methods__ = []
    __owner_methods__ = []
    __registered_methods__ = []

    @declared_attr
    def __tablename__(cls):
        # Correct English attaches 'es' to plural forms which end in 's'
        if cls.__name__.lower()[-1:] == 's':
            return "%ses" % cls.__name__.lower()
        return "%ss" % cls.__name__.lower()

    id = Column(Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def _id(cls):
        return synonym("id")

    _created = Column(DateTime, default=dt.datetime.utcnow)
    _updated = Column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    _etag = Column(String(50))

    # This needs to be a function, as it has a ForeignKey in a mixin. The
    # function makes binding at a later point possible
    @declared_attr
    def _author(cls):
        return Column(Integer, ForeignKey("users.id"))  # , nullable=False)


Base = declarative_base(cls=BaseModel)


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
    __projected_fields__ = ['permissions']

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
    permissions = relationship("Permission", foreign_keys="Permission.user_id",
                               backref="user", cascade="all, delete")
    groups = relationship("GroupUserMember",
                          foreign_keys="GroupUserMember.user_id",
                          backref="user", cascade="all, delete")
    sessions = relationship("Session", foreign_keys="Session.user_id",
                            backref="user", cascade="all, delete")
    eventsignups = relationship("EventSignup",
                                foreign_keys="EventSignup.user_id",
                                backref="user", cascade="all, delete")


class Permission(Base):
    """Intermediate table for 'many-to-many' mapping
        split into one-to-many from Group and many-to-one with User
    We need to use a class here in stead of a table because of additional data
        expiry_date
    """
    __description__ = {
        'general': "Mapping between users and their roles. Assigning a user to"
        " a role will add permissions for certain resources.",
        'fields': {
            'role': "Possible roles can be extracted with the /roles endpoint"
        }
    }
    __expose__ = True

    __owner__ = ['user_id']
    __owner_methods__ = ['GET']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(CHAR(20), nullable=False)
    expiry_date = Column(DateTime, nullable=False)

    # user = relationship("User", foreign_keys=user_id, backref="permissions")


class Group(Base):
    __description__ = {
        'general': "This resource describes the different teams in AMIV."
        "This is primarily a mailing list. To see "
        "the subscriptions, have a look at '/groupusermembers' and "
        "'groupaddressmembers'.",
        'fields': {
            'is_public': "A public group can get subscriptions from external"
            " users. If False, only AMIV-Members can subscribe to this list.",
            'address': "The address of the new forward: <address>@amiv.ethz.ch"
        }}
    __expose__ = True
    __projected_fields__ = ['user_subscribers', 'address_subscribers']

    __owner__ = ['owner_id']
    __owner_methods__ = ['GET', 'DELETE']

    name = Column(Unicode(100), unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    owner = relationship(User, foreign_keys=owner_id)

    user_subscribers = relationship("GroupUserMember", backref="group",
                                    cascade="all, delete")
    address_subscribers = relationship("GroupAddressMember", backref="group",
                                       cascade="all, delete")
    addresses = relationship("ForwardAddress", backref="group",
                             cascade="all, delete")


class ForwardAddress(Base):
    __description__ = {
        'general': "An email address associated with a group. By adding "
        "an address here, all mails sent to that address will be forwarded "
        "to all members of the associated group.",
        'fields': {
            'address': "E-Mail address to forward"
        }
    }
    __expose__ = True
    __projected_fields__ = ['group']

    __owner__ = ["group.owner_id"]
    __owner_methods__ = ['GET']

    address = Column(Unicode(100), unique=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupUserMember(Base):
    __description__ = {
        'general': "Assignment of registered users to groups."
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['user_id', 'group.owner_id']
    __owner_methods__ = ['GET', 'POST', 'DELETE']

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    group_id = Column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)

    # group = relationship("Group", backref="user_subscribers")
    # user = relationship("User", foreign_keys=user_id)


class GroupAddressMember(Base):
    __description__ = {
        'general': "Assignment of unregistered users to groups. Does only "
        "work if the group is public"
    }
    __expose__ = True
    __projected_fields__ = ['group']

    __owner__ = ['group.owner_id']
    __owner_methods__ = ['GET', 'POST', 'DELETE']
    __public_methods__ = ['POST', 'DELETE']

    email = Column(Unicode(100))
    group_id = Column(
        Integer, ForeignKey("groups.id"), nullable=False)

    """for unregistered users"""
    _token = Column(CHAR(20), unique=True, nullable=True)
    _confirmed = Column(Boolean, default=False)


class Session(Base):
    __description__ = {
        'general': "A session is used to authenticate a user after he "
        " provided login data. To acquire a session use POST, which will "
        " give you a token to use as the user field of HTTP basic auth "
        " header with an empty password. POST requires user and password "
        " fields.",
        'methods': {
            'POST': "Login and aquire a login token. Post the fields "
            "'user' and 'password', the response will contain the token."
        }
    }
    __expose__ = True
    __projected_fields__ = ['user']

    __public_methods__ = ['POST']
    __owner__ = ['user_id']
    __owner_methods__ = ['GET', 'DELETE']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(Text)

    # user = relationship("User", foreign_keys=user_id, backref="sessions")


class Event(Base):
    __description__ = {
        'general': "An Event is basically everything happening in the AMIV.",
        'methods': {
            'GET': "You are always allowed, even without session, to view "
            "AMIV-Events"
        },
        'fields': {
            'price': 'Price of the event as Integer in Rappen.',
            'additional_fields': "must be provided in form of a JSON-Schema. "
            "You can add here fields you want to know from people signing up "
            "going further than their email-address",
            'is_public': "If False, only AMIV-Members can sign up for this "
            "event",
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
    is_public = Column(Boolean, default=False, nullable=False)
    price = Column(Integer)  # Price in Rappen
    spots = Column(Integer, nullable=False)
    time_register_start = Column(DateTime)
    time_register_end = Column(DateTime)
    additional_fields = Column(Text)
    show_infoscreen = Column(Boolean, default=False)
    show_website = Column(Boolean, default=False)
    show_announce = Column(Boolean, default=False)

    # Images
    img_thumbnail = Column(CHAR(100))  # This will be modified in schemas.py!
    img_banner = Column(CHAR(100))  # This will be modified in schemas.py!
    img_poster = Column(CHAR(100))  # This will be modified in schemas.py!
    img_infoscreen = Column(CHAR(100))  # This will be modified in schemas.py!

    title_de = Column(UnicodeText)
    title_en = Column(UnicodeText)
    description_de = Column(UnicodeText)
    description_en = Column(UnicodeText)
    catchphrase_de = Column(UnicodeText)
    catchphrase_en = Column(UnicodeText)
    
    # relationships
    signups = relationship("EventSignup", backref="event",
                           cascade="all, delete")


class EventSignup(Base):
    __description__ = {
        'general': "You can signup here for an existing event inside of the "
        "registration-window. External Users can only sign up to public "
        "events.",
        'fields': {
            'additional fields': "Data-schema depends on 'additional_fields' "
            "from the mapped event. Please provide in json-format.",
            'user_id': "To sign up as external user, set 'user_id' to '-1'",
            'email': "For registered users, this is just a projection of your "
            "general email-address. External users need to provide their email"
            " here.",
        }}
    __expose__ = True
    __projected_fields__ = ['event', 'user']

    __owner__ = ['user_id']
    __owner_methods__ = ['POST', 'GET', 'PATCH', 'DELETE']
    __public_methods__ = []

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(CHAR(100), ForeignKey("users.email"))
    additional_fields = Column(Text)

    """for unregistered users"""
    _email_unreg = Column(Unicode(100))
    _token = Column(CHAR(20), unique=True, nullable=True)
    _confirmed = Column(Boolean, default=False)


class File(Base):
    """This is a file that belongs to a study document.

    An additional name for the file is possible
    A studydocument needs to be referenced

    Files can only be created and deleted (or both, put), patching them is not
    intended
    """
    __expose__ = True

    __owner__ = ['_author']  # This permitts everybody to post here!
    __owner_methods__ = ['GET', 'POST', 'PUT', 'DELETE']
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
    __owner_methods__ = ['GET', 'PUT', 'POST', 'PATCH', 'DELETE']
    __registered_methods__ = ['GET']

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
                         cascade="all, delete")


class JobOffer(Base):
    __expose__ = True

    __public_methods__ = ['GET']

    company = Column(Unicode(30))

    logo = Column(CHAR(100))  # This will be modified in schemas.py!
    pdf = Column(CHAR(100))  # This will be modified in schemas.py!
    time_end = Column(DateTime)

    title_de = Column(UnicodeText)
    title_en = Column(UnicodeText)
    description_de = Column(UnicodeText)
    description_en = Column(UnicodeText)

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

    user_id = Column(Integer)
    timestamp = Column(DateTime)
    type = Column(Enum("beer", "kaffi"))
    slot = Column(Integer)

#
# Permissions for custom endpoints
# These are not created in the database due to __abstract__ = True
# utils.get_class_for_resource will find these
#

class Storage(Base):
    __expose__ = False  # Don't create a schema
    __abstract__ = True
    __registered_methods__ = ['GET']
    __description__ = {
        'general': 'Endpoint to download files, get the URLs via /files'
    }


class Roles(Base):
    __expose__ = False  # Don't create a schema
    __abstract__ = True
    __registered_methods__ = ['GET']
    __description__ = {
        'general': 'Resource to get available roles. Only GET is supported'
    }
