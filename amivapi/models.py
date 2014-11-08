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
    DECIMAL,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, synonym, backref

from eve.io.sql.decorators import registerSchema


class BaseModel(object):
    """Mixin for common columns."""
    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return "%ss" % cls.__name__

    id = Column(Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def _id(cls):
        return synonym("id")

    _created = Column(DateTime, default=dt.datetime.utcnow)
    _updated = Column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    _etag = Column(String(50))


Base = declarative_base(cls=BaseModel)


class GroupMembership(Base):
    """Intermediate table for many-to-many mapping."""
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("Groups.id"), nullable=False)
    expiry_date = Column(DateTime)

    # group = relationship("Group")


@registerSchema("users")
class User(Base):
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
                        nullable=False, default="none")

    # groups = relationship(GroupMembership)


@registerSchema("groups")
class Group(Base):
    name = Column(Unicode(30))

    # members = relationship("User", secondary="GroupMember")


class EmailForwardSubscriber(Base):
    """Intermediate table for many-to-many mapping."""
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    forward_id = Column(
        Integer, ForeignKey("EmailForwards.id"), nullable=False)


@registerSchema("emails")
class EmailForward(Base):
    address = Column(Unicode(100), unique=True)
    owner_id = Column(Integer, ForeignKey("Users.id"), nullable=False)

    owner = relationship(User)
    subscriber = relationship(EmailForwardSubscriber)


@registerSchema("sessions")
class Session(Base):
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    signature = Column(CHAR(64))

    # user = relationship(User, backref=backref('sessions'))


@registerSchema("events")
class Event(Base):
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


@registerSchema("signups")
class EventSignup(Base):
    event_id = Column(Integer, ForeignKey("Events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    email = Column(Unicode(100))
    extra_data = Column(Text)


@registerSchema("files")
class File(Base):
    name = Column(Unicode(100))
    type = Column(String(30))
    size = Column(Integer)
    content_url = Column(String(200))


@registerSchema("studydocuments")
class StudyDocument(Base):
    name = Column(Unicode(100))
    type = Column(String(30))
    exam_session = Column(String(10))
    department = Column(Enum("itet", "mavt"))
    lecture = Column(Unicode(100))
    professor = Column(Unicode(100))
    semester = Column(Integer)
    author_id = Column(Integer, ForeignKey("Users.id"), nullable=True)
    author_name = Column(Unicode(100))


@registerSchema("joboffers")
class JobOffer(Base):
    company = Column(Unicode(30))
    title = Column(Unicode(100))
    description = Column(UnicodeText)
    logo_id = Column(Integer, ForeignKey("Files.id"))
    pdf_id = Column(Integer, ForeignKey("Files.id"))
    time_end = Column(DateTime)
