import datetime as dt

from sqlalchemy import (
    Column,
    Unicode,
    UnicodeText,
    CHAR,
    String,
    Text,
    Integer,
    ForeignKey,
    Date,
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

    username = Column(CHAR(50), unique=True, nullable=False)
    password = Column(CHAR(100))  # base64 encoded hash data
    firstname = Column(Unicode(50), nullable=False)
    lastname = Column(Unicode(50), nullable=False)
    birthday = Column(Date)
    legi = Column(CHAR(8))
    rfid = Column(CHAR(6))
    nethz = Column(String(30))
    department = Column(Enum("itet", "mavt"))
    phone = Column(String(20))
    ldapAddress = Column(Unicode(200))
    gender = Column(Enum("male", "female"), nullable=False)
    email = Column(CHAR(100), nullable=False, unique=True)
    membership = Column(Enum("none", "regular", "extraordinary", "honorary"),
                        nullable=False, default="none", server_default="none")

    # relationships
    permissions = relationship("Permission", foreign_keys="Permission.user_id",
                               backref="user", cascade="all, delete")
    forwards = relationship("ForwardUser", foreign_keys="ForwardUser.user_id",
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


class Forward(Base):
    __description__ = {
        'general': "This resource describes the different email-lists. To see "
        "the subscriptions, have a look at '/forwardusers' and "
        "'forwardaddresses'.",
        'fields': {
            'is_public': "A public Forward can get subscriptions from external"
            " users. If False, only AMIV-Members can subscribe to this list.",
            'address': "The address of the new forward: <address>@amiv.ethz.ch"
        }}
    __expose__ = True
    __projected_fields__ = ['user_subscribers', 'address_subscribers']

    __owner__ = ['owner_id']
    __owner_methods__ = ['GET', 'DELETE']

    address = Column(Unicode(100), unique=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    owner = relationship(User, foreign_keys=owner_id)

    # relationships
    user_subscribers = relationship("ForwardUser", backref="forward",
                                    cascade="all, delete")
    address_subscribers = relationship("ForwardAddress", backref="forward",
                                       cascade="all, delete")


class ForwardUser(Base):
    __description__ = {
        'general': "Assignment of registered users to forwards."
    }
    __expose__ = True
    __projected_fields__ = ['forward', 'user']

    __owner__ = ['user_id', 'forward.owner_id']
    __owner_methods__ = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    forward_id = Column(
        Integer, ForeignKey("forwards.id", ondelete="CASCADE"), nullable=False)

    # forward = relationship("Forward", backref="user_subscribers")
    # user = relationship("User", foreign_keys=user_id)


class ForwardAddress(Base):
    __description__ = {
        'general': "Assignment of unregisterd users to forwards. Does only "
        "work if the forward is poblic"
    }
    __expose__ = True
    __projected_fields__ = ['forward']

    __owner__ = ['forward.owner_id']
    __owner_methods__ = ['GET']
    __public_methods__ = ['POST', 'DELETE']

    email = Column(Unicode(100))
    forward_id = Column(
        Integer, ForeignKey("forwards.id"), nullable=False)

    """for unregistered users"""
    _token = Column(CHAR(20), unique=True, nullable=True)
    _confirmed = Column(Boolean, default=False)


class Session(Base):
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
    # Images
    img_thumbnail = Column(CHAR(100))  # This will be modified in schemas.py!
    img_web = Column(CHAR(100))  # This will be modified in schemas.py!
    img_1920_1080 = Column(CHAR(100))  # This will be modified in schemas.py!

    # Translatable fields
    # The relationship exists to ensure cascading delete and will be hidden
    # from the user
    title_id = Column(Integer, ForeignKey('translationmappings.id'))
    title_rel = relationship("TranslationMapping", cascade="all, delete",
                             foreign_keys=title_id)
    description_id = Column(Integer, ForeignKey('translationmappings.id'))
    description_rel = relationship("TranslationMapping", cascade="all, delete",
                                   foreign_keys=description_id)

    # relationships
    signups = relationship("EventSignup", backref="event",
                           cascade="all, delete")


class EventSignup(Base):
    __description__ = {
        'general': "You can signup here for an existing event inside of the "
        "registration-window. External Users can only sign up to public "
        "events.",
        'fields': {
            'extra_data': "Data-schema depends on 'additional_fields' from the"
            " mapped event. Please provide in json-format.",
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
    extra_data = Column(Text)

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

    # Translatable fields
    # The relationship exists to ensure cascading delete and will be hidden
    # from the user
    title_id = Column(Integer, ForeignKey('translationmappings.id'))
    title_rel = relationship("TranslationMapping", cascade="all, delete",
                             foreign_keys=title_id)
    description_id = Column(Integer, ForeignKey('translationmappings.id'))
    description_rel = relationship("TranslationMapping", cascade="all, delete",
                                   foreign_keys=description_id)


# Language ids are in here
class TranslationMapping(Base):
    __expose__ = True

    content = relationship("Translation",
                           cascade="all, delete", uselist=True)


# This is the translated content
class Translation(Base):
    __expose__ = True

    localization_id = Column(Integer, ForeignKey('translationmappings.id'),
                             nullable=False)
    language = Column(Unicode(10), nullable=False)
    content = Column(UnicodeText, nullable=False)

    __table_args__ = (UniqueConstraint('localization_id', 'language'),)


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
