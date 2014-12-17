import datetime as dt

from sqlalchemy import (
    Column,
    inspect,
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
    DECIMAL,
)
from sqlalchemy.ext import hybrid
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.schema import Table


""" Eve exspects the resource names to be equal to the table names. Therefore
we generate all names from the Class names. Please choose classnames carefully,
as changing them might break a lot of code """


""" About Authentification

To turn off authentification completely set the property
__public_methods__ to contain the method. If authentification is turned off,
then the logintoken off the user is not even considered and any action will be
done by user -1(anonymous).

Everything from now on requires the method to not be public.

If the user has a role, which is listed to be an admin for the endpoint in
permission_matrix.py, then g.resource_admin_access will be set during the
request. Furthermore no filters will be applied based on permissions to any
requests to that endpoint.

A class can have an __owner__ property. That property describes is a list of
fields, which contains the user id of somebody who can GET the object and use
the methods described by __owner_methods__. This works even through a relation.

When a POST is allowed by the owner, then it will be permitted if the item to
be created will be owned by the logged in user after the request is done.

For more details see the following files:
auth.py
permission_matrix.py
"""


class BaseModel(object):
    """Mixin for common columns."""

    """__abstract__ makes SQL Alchemy not create a table for this class """
    __abstract__ = True

    """ All classes which overwrite this with True will get exposed as a
    resource """
    __expose__ = False

    """ This is a list of fields, which are added to the projection created by
    eve. Add any additional field to be delivered on GET requests by default
    in the subclasses. """
    __projected_fields__ = []

    __public_methods__ = []
    __owner_methods__ = []
    __registered_methods__ = []

    @declared_attr
    def __tablename__(cls):
        """ Correct English attaches 'es' to plural forms which end in 's' """
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

    """ This needs to be a function, as it has a ForeignKey in a mixin. The
    function makes binding at a later point possible """
    @declared_attr
    def _author(cls):
        return Column(Integer, ForeignKey("users.id"), nullable=False)

    def jsonify(self):
        """
        Used to dump related objects to json
        """
        relationships = inspect(self.__class__).relationships.keys()
        mapper = inspect(self)
        attrs = [a.key for a in mapper.attrs if
                 a.key not in relationships
                 and a.key not in mapper.expired_attributes]
        attrs += [a.__name__ for a in
                  inspect(self.__class__).all_orm_descriptors
                  if a.extension_type is hybrid.HYBRID_PROPERTY]
        return dict([(c, getattr(self, c, None)) for c in attrs])


Base = declarative_base(cls=BaseModel)


class User(Base):
    __expose__ = True
    __projected_fields__ = ['groups']

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


class Permission(Base):
    """Intermediate table for 'many-to-many' mapping
        split into one-to-many from Group and many-to-one with User
    We need to use a class here in stead of a table because of additional data
        expiry_date
    """
    __expose__ = True

    __owner__ = ['user_id']
    __owner_methods__ = ['GET']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(CHAR(20), nullable=False)
    expiry_date = Column(DateTime)

    user = relationship("User", foreign_keys=user_id, backref="permissions")


class Forward(Base):
    __expose__ = True
    __projected_fields__ = ['user_subscribers', 'address_subscribers']

    __owner__ = ['owner_id']
    __owner_methods__ = ['GET', 'DELETE']

    address = Column(Unicode(100), unique=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship(User, foreign_keys=owner_id)


class ForwardUser(Base):
    __expose__ = True
    __projected_fields__ = ['forward', 'user']

    __owner__ = ['user_id', 'forward.owner_id']
    __owner_methods__ = ['GET', 'POST', 'DELETE']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    forward_id = Column(
        Integer, ForeignKey("forwards.id"), nullable=False)

    forward = relationship("Forward", backref="user_subscribers")
    user = relationship("User", foreign_keys=user_id)


class ForwardAddress(Base):
    __expose__ = True
    __projected_fields__ = ['forward']

    __owner__ = ['forward.owner_id']
    __owner_methods__ = ['GET', 'POST', 'DELETE']

    address = Column(Unicode(100))
    forward_id = Column(
        Integer, ForeignKey("forwards.id"), nullable=False)

    forward = relationship("Forward", backref="address_subscribers")


class Session(Base):
    __expose__ = True
    __projected_fields__ = ['user']

    __public_methods__ = ['POST']
    __owner__ = ['user_id']
    __owner_methods__ = ['GET']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(CHAR(10424), unique=True)

    user = relationship("User", foreign_keys=user_id, backref="sessions")


class Event(Base):
    __expose__ = True
    __projected_fields__ = ['signups']

    __public_methods__ = ['GET']

    title = Column(Unicode(50))
    time_start = Column(DateTime)
    time_end = Column(DateTime)
    location = Column(Unicode(50))
    description = Column(UnicodeText)
    is_public = Column(Boolean, default=False, nullable=False)
    price = Column(String(10))
    spots = Column(Integer, nullable=False)
    time_register_start = Column(DateTime)
    time_register_end = Column(DateTime)
    additional_fields = Column(Text)

    # images


class EventSignup(Base):
    __expose__ = True
    __projected_fields__ = ['event', 'user']

    __owner__ = ['user_id']
    __owner_methods__ = ['GET', 'PATCH', 'DELETE']

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(Unicode(100))
    extra_data = Column(Text)

    """Data-Mapping: many-to-one"""
    user = relationship("User", foreign_keys=user_id)

    """Data-Mapping: many-to-one"""
    event = relationship("Event", backref="signups")


class File(Base):
    __expose__ = True

    __owner__ = ['_author']  # This permitts everybody to post here!
    __owner_methods__ = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    name = Column(Unicode(100))
    data = Column(CHAR(100))


"""
Mapping from StudyDocuments to File
We don't want to have an extra Column in Files, therefore we need this table
"""
studydocuments_files_association = Table(
    'studydocuments_files_association', Base.metadata,
    Column("file_id", Integer, ForeignKey("files.id")),
    Column("studydocument", Integer, ForeignKey("studydocuments.id"))
)


class StudyDocument(Base):
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

    """Mapping to Files"""
    files = relationship("File", secondary=studydocuments_files_association)


class JobOffer(Base):
    __expose__ = True

    __public_methods__ = ['GET']

    company = Column(Unicode(30))
    title = Column(Unicode(100))
    description = Column(UnicodeText)
    logo = CHAR(100)  # The Schema here is changed to type: media
    pdf_id = Column(Integer, ForeignKey("files.id"))
    time_end = Column(DateTime)


# Confirm Actions for unregistered email-adresses
class Confirm(Base):
    token = Column(CHAR(20), unique=True, nullable=False)
    method = Column(String(10))
    ressource = Column(String(50))
    data = Column(String(1000))
    expiry_date = Column(DateTime)
