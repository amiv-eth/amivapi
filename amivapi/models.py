# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import datetime as dt
import json

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
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, synonym, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.types import TypeDecorator
from sqlalchemy.exc import InvalidRequestError

from amivapi.settings import PASSWORD_CONTEXT


#
# Eve exspects the resource names to be equal to the table names. Therefore
# we generate all names from the Class names. Please choose classnames
# carefully, as changing them might break a lot of code
#


class JSON(TypeDecorator):
    """ Column type to transparently handle JSONified content.

    Converts between python objects and a String column in the database.

    Usage:
        JSON(255) (implies a String(255) column)

    See also:
        http://docs.sqlalchemy.org/en/rel_0_7/core/types.html#marshal-json-strings
    """
    impl = String

    def process_bind_param(self, value, dialect):
        """ Application -> Database """
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        """ Database -> Application """
        if value is not None:
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                raise ValueError("Invalid JSON found in database: %r", value)

        return value


class JSONText(JSON):
    impl = Text


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
    # These fields are embedded by default meaning that not only the related
    # ids are used, but the whole object included
    __embedded_fields__ = []

    # These can contain a list of methods which need some kind of
    # authorization. If nothing is set only admins can access the method
    __public_methods__ = []
    __owner_methods__ = []
    __registered_methods__ = []
    __owner__ = []

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

    @declared_attr
    def __self__(cls):
        """ This makes it possible to reference fields indirectly with
        User.__self__.sessions. We use this as a workaround, as the lookup dict
        for eve can not contain sqlalchemy operators for a relation.

            { "sessions": "indirect_any(\"token\")" }

        This would fail cause eve_sqlalchemy first checks wether sessions is a
        relation and therefore never reaches the custom operator clause.

            { "__self__": "indirect_any(\"sessions.token\")" }

        This works as __self__ is not a relation. """
        return cls

    @classmethod
    def indirect_any(cls, querystring):
        """ This is a custom SQL alchemy operator, used to check if any field
        is matched over various relations

        This is used to check indirect permissions in authorization.py

        When the parser hits one to many relations it will create any clauses

        Example:
            User.recursive_any("groups.addresses.address, \"it@amiv.ethz.ch\"")

            this will return all users, which are in a group which receives
            emails from it@amiv.ethz.ch

        @argument querystring: String of two comma seperated arguments. The
                               first is the field which is to be checked. The
                               second is the value to match.

        @returns: sqlalchemy statement """

        field, value = map(unicode.strip, querystring.split(','))

        parts = field.strip().split('.')
        relation = getattr(cls, parts[0])

        try:
            # This will work for many-to-one relationships
            return relation.has(**{'.'.join(parts[1:]): value})
        except InvalidRequestError:
            # This will work for one-to-many relationships
            # In this case we accept if there is any related object which
            # satisfies the requirement
            return relation.any(**{'.'.join(parts[1:]): value})


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


class Group(Base):
    __description__ = {
        'general': "This resource describes the different teams in AMIV."
        "A group can grant API permissions and can be reached with several "
        "addresses. To see the addresses of this group, see /groupaddresses"
        "To see the members, have a look at '/groupmembers'. "
        "To see the addresses messages are forwarded to, see /groupforwards",
        'fields': {
            'allow_self_enrollment': "If true, the group can be seen by all "
            "users and they can subscribe themselves",
            'has_zoidberg_share': "Wether the group has a share in the amiv "
            "storage",
            "permissions": "permissions the group grants. has to be according "
            "to the jsonschema available at /notyetavailable"  # TODO!
        }}
    __expose__ = True
    __projected_fields__ = ['members', 'addresses', 'forwards']
    __embedded_fields__ = ['members', 'addresses', 'forwards']

    __owner__ = ['moderator_id', 'members.user_id']
    __owner_methods__ = ['GET']  # Only admins can modify the group itself!

    __registered_methods__ = ['GET']  # All users can check for open groups

    name = Column(Unicode(100), unique=True, nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allow_self_enrollment = Column(Boolean, default=False, nullable=False)

    has_zoidberg_share = Column(Boolean, default=False, nullable=False)

    permissions = Column(JSONText)

    owner = relationship(User, foreign_keys=moderator_id)

    members = relationship("GroupMember", backref="group", cascade="all")
    addresses = relationship("GroupAddress", backref="group", cascade="all")
    forwards = relationship("GroupForward", backref="group", cascade="all")


class GroupAddress(Base):
    __description__ = {
        'general': "An email address associated with a group. By adding "
        "an address here, all mails sent to that address will be forwarded "
        "to all members and forwards of the associated group.",
        'fields': {
            'email': "E-Mail address for the group",
        }
    }
    __expose__ = True
    __projected_fields__ = ['group']

    __owner__ = ["group.moderator_id"]
    __owner_methods__ = ['GET', 'DELETE']

    # All registered users must be able to post
    # Only way to allow moderators to create addresses
    __registered_methods__ = ['POST']

    email = Column(Unicode(100), unique=True, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupMember(Base):
    __description__ = {
        'general': "Assignment of registered users to groups."
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['user_id', 'group.moderator_id']
    __owner_methods__ = ['GET', 'DELETE']

    __registered_methods__ = ['POST']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupForward(Base):
    __description__ = {
        'general': "All messages to the group will be additionally forwarded"
        "to this address The group will NOT receive messages sent to this "
        "address, see /groupaddress for this.",
        'fields': {
            'email': "E-Mail address to which mails will be forwarded"
        }
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['group.moderator_id']
    __owner_methods__ = ['GET', 'DELETE']

    __registered_methods__ = ['POST']

    email = Column(Unicode(100), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


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
        return len(self.signups)

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
                           cascade="all")


class EventSignup(Base):
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
    __owner_methods__ = ['GET']

    user_id = Column(Integer, ForeignKey('users.id'))
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
