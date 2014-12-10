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

    username = Column(Unicode(50), unique=True, nullable=False)
    password = Column(Unicode(50))
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
    email = Column(Unicode(100), nullable=False, unique=True)
    membership = Column(Enum("none", "regular", "extraordinary", "honorary"),
                        nullable=False, default="none", server_default="none")


class Group(Base):
    __expose__ = True
    __projected_fields__ = ['members']

    name = Column(Unicode(30))


class GroupMembership(Base):
    """Intermediate table for 'many-to-many' mapping
        split into one-to-many from Group and many-to-one with User
    We need to use a class here in stead of a table because of additional data
        expiry_date
    """
    __expose__ = True

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    expiry_date = Column(DateTime)

    user = relationship("User", backref="groups")
    group = relationship("Group", backref="members")


class Forward(Base):
    __expose__ = True
    __projected_fields__ = ['user_subscribers', 'address_subscribers']

    address = Column(Unicode(100), unique=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship(User)


class ForwardUser(Base):
    __expose__ = True
    __projected_fields__ = ['forward', 'user']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    forward_id = Column(
        Integer, ForeignKey("forwards.id"), nullable=False)

    forward = relationship("Forward", backref="user_subscribers")
    user = relationship("User")


class ForwardAddress(Base):
    __expose__ = True
    __projected_fields__ = ['forward']

    address = Column(Unicode(100))
    forward_id = Column(
        Integer, ForeignKey("forwards.id"), nullable=False)

    forward = relationship("Forward", backref="address_subscribers")


class Session(Base):
    __expose__ = True
    __projected_fields__ = ['user']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    signature = Column(CHAR(64))

    user = relationship("User", backref="sessions")


class Event(Base):
    __expose__ = True
    __projected_fields__ = ['signups']

    title = Column(Unicode(50))
    time_start = Column(DateTime)
    time_end = Column(DateTime)
    location = Column(Unicode(50))
    description = Column(UnicodeText)
    is_public = Column(Boolean)
    price = Column(DECIMAL())
    spots = Column(Integer)
    time_register_start = Column(DateTime)
    time_register_end = Column(DateTime)
    additional_fields = Column(Text)

    # images


class EventSignup(Base):
    __expose__ = True
    __projected_fields__ = ['event', 'user']

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(Unicode(100))
    extra_data = Column(Text)

    """Data-Mapping: many-to-one"""
    user = relationship("User")

    """Data-Mapping: many-to-one"""
    event = relationship("Event", backref="signups")


class File(Base):
    __expose__ = True

    name = Column(Unicode(100))
    type = Column(String(30))
    size = Column(Integer)
    content_url = Column(String(200))


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

    name = Column(Unicode(100))
    type = Column(String(30))
    exam_session = Column(String(10))
    department = Column(Enum("itet", "mavt"))
    lecture = Column(Unicode(100))
    professor = Column(Unicode(100))
    semester = Column(Integer)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_name = Column(Unicode(100))

    """Mapping to Files"""
    files = relationship("File", secondary=studydocuments_files_association)


class JobOffer(Base):
    __expose__ = True
    company = Column(Unicode(30))
    title = Column(Unicode(100))
    description = Column(UnicodeText)
    logo_id = Column(Integer, ForeignKey("files.id"))
    pdf_id = Column(Integer, ForeignKey("files.id"))
    time_end = Column(DateTime)


#Confirm Actions for unregistered email-adresses
class Confirm(Base):
    token = Column(CHAR(20), unique=True, nullable=False)
    method = Column(String(10))
    ressource = Column(String(50))
    data = Column(String(1000))
    expiry_date = Column(DateTime)
