# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities for db."""


import datetime as dt
import json

from sqlalchemy.types import TypeDecorator
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import synonym
from sqlalchemy import (
    Column,
    Text,
    String,
    Integer,
    ForeignKey,
    DateTime,
)

# SQL base etc

#
# Eve exspects the resource names to be equal to the table names. Therefore
# we generate all names from the Class names. Please choose classnames
# carefully, as changing them might break a lot of code
#


class JSON(TypeDecorator):
    """Column type to transparently handle JSONified content.

    Converts between python objects and a String column in the database.

    Usage:
        JSON(255) (implies a String(255) column)

    See also:
        http://docs.sqlalchemy.org/en/rel_0_7/core/types.html#marshal-json-strings
    """

    impl = String

    def process_bind_param(self, value, dialect):
        """Application -> Database."""
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        """Database -> Application."""
        if value is not None:
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                raise ValueError("Invalid JSON found in database: %r", value)

        return value


class JSONText(JSON):
    """Column to handle variable length JSON."""

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
        """Make name for table."""
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
        """Make own class available to models.

        This makes it possible to reference fields indirectly with
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
        """Check if any field is matched over various relations.

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
"""Declarative base to use for all models."""
