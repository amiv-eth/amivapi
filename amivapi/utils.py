# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities."""


from base64 import urlsafe_b64encode
from os import urandom
import smtplib
from email.mime.text import MIMEText
from copy import deepcopy
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
from flask import Config, g, current_app as app

from eve.utils import config, request_method
from eve_sqlalchemy.decorators import registerSchema
from eve_sqlalchemy.validation import ValidatorSQL

from amivapi.settings import ROOT_DIR


def get_config():
    """Load the config from settings.py and updates it with config.cfg.

    :returns: Config dictionary
    """
    config = Config(ROOT_DIR)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("config.cfg")
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                      "`python manage.py create_config`.")

    return config


def get_class_for_resource(resource):
    """Utility function to get SQL Alchemy model associated with a resource.

    :param resource: Name of a resource
    :returns: SQLAlchemy model associated with the resource from models.py
    """
    if resource in config.DOMAIN:
        return config.DOMAIN[resource]['sql_model']
    else:
        return None


def token_generator(size=6):
    """Generate a random string of elements of chars.

    :param size: length of the token
    :returns: a random token
    """
    return urlsafe_b64encode(urandom(size))[0:size]


def recursive_any_getattr(obj, path):
    """Recursive gettattr.

    Given some object and a path, retrive any value, which is reached with
    this path. Lists are looped through.

    @argument obj: Object to start with
    @argument path: List of attribute names

    @returns: List of values
    """
    if len(path) == 0:
        if isinstance(obj, list):
            return obj
        return [obj]

    if isinstance(obj, list):
        results = []
        for item in obj:
            results.extend(recursive_any_getattr(item, path))
        return results

    next_field = getattr(obj, path[0])

    return recursive_any_getattr(next_field, path[1:])


def get_owner(model, id):
    """Search for the owner(s) of a data-item.

    :param model: the SQLAlchemy-model (in models.py)
    :param _id: The id of the item (unique for each model)
    :returns: a list of owner-ids
    """
    db = app.data.driver.session
    doc = db.query(model).get(id)
    if not doc or not hasattr(model, '__owner__'):
        return None
    ret = []
    for path in doc.__owner__:
        ret.extend(recursive_any_getattr(doc, path.split('.')))
    return ret


def mail(sender, to, subject, text):
    """Send a mail to a list of recipients.

    :param from: From address
    :param to: List of recipient addresses
    :param subject: Subject string
    :param text: Mail content
    """
    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ';'.join(to)

    try:
        s = smtplib.SMTP(config.SMTP_SERVER)
        try:
            s.sendmail(msg['From'], to, msg.as_string())
        except smtplib.SMTPRecipientsRefused as e:
            print("Failed to send mail:\nFrom: %s\nTo: %s\nSubject: %s\n\n%s"
                  % (sender, str(to), subject, text))
        s.quit()
    except smtplib.SMTPException as e:
        print("SMTP error trying to send mails: %s" % e)


EMAIL_REGEX = '^.+@.+$'


class ValidatorAMIV(ValidatorSQL):
    """Validator subclass adding more validation for special fields."""

    def _validate_not_patchable(self, enabled, field, value):
        """Custom Validator to inhibit patching of the field.

        e.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled (bool): Boolean, should be true
            field (string): field name.
            value: field value.
        """
        if enabled and (request_method() == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_not_patchable_unless_admin(self, enabled, field, value):
        """Inhibit patching of the field.

        e.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled (bool): Boolean, should be true
            field (string): field name.
            value: field value.
        """
        if enabled and (request_method() == 'PATCH') and not g.resource_admin:
            self._error(field, "this field can not be changed with PATCH "
                        "unless you have admin rights.")

    def _validate_unique_combination(self, unique_combination, field, value):
        """Validate that a combination of fields is unique.

        e.g. user with id 1 can have several eventsignups for different events,
        but only 1 eventsignup for event with id 42

        unique_combination should be a list of other fields

        Note: Make sure that other fields actually exists (setting them to
        required etc)

        Args:
            unique_combination (list): combination fields
            field (string): field name.
            value: field value.
        """
        lookup = {field: value}  # self
        for other_field in unique_combination:
            lookup[other_field] = self.document.get(other_field)

        # If we are patching the issue is more complicated, some fields might
        # have to be checked but are not part of the document because they will
        # not be patched. We have to load them from the database
        patch = (request_method() == 'PATCH')
        if patch:
            original = self._original_document
            for key in unique_combination:
                if key not in self.document.keys():
                    lookup[key] = original[key]

        # Now check database
        if app.data.find_one(self.resource, None, **lookup) is not None:
            self._error(field, "value already exists in the database in " +
                        "combination with values for: %s" %
                        unique_combination)


def make_domain(model):
    """Make Eve domain for a model.

    Uses Eve-SQLAlchemies registerSchema and adds a little bit of our own.
    """
    tbl_name = model.__tablename__

    registerSchema(tbl_name)(model)
    domain = model._eve_schema

    for field in model.__projected_fields__:
        domain[tbl_name]['datasource']['projection'].update(
            {field: 1}
        )
        if not('embedded_fields' in domain[tbl_name]):
            domain[tbl_name]['embedded_fields'] = {}
        for field in model.__embedded_fields__:
            domain[tbl_name]['embedded_fields'].update(
                {field: 1}
            )

    # Add owner and method permissions to domain
    domain[tbl_name]['owner'] = model.__owner__
    domain[tbl_name]['public_methods'] = model.__public_methods__
    domain[tbl_name]['public_item_methods'] = model.__public_methods__
    domain[tbl_name]['registered_methods'] = model.__registered_methods__
    domain[tbl_name]['owner_methods'] = model.__owner_methods__

    # SQLAlchemy model (needed for owner evaluation)
    domain[tbl_name]['sql_model'] = model

    # For documentation
    domain[tbl_name]['description'] = model.__description__

    # Users should not provide _author fields
    domain[tbl_name]['schema']['_author'].update({'readonly': True})

    # Remove id field (eve will provide id)
    domain[tbl_name]['schema'].pop('id')

    return domain


def register_domain(app, domain):
    """Add all resources in a domain to the app.

    The domain has to be deep-copied first because eve will modify it
    (since it heavily relies on setdefault()), which can cause problems
    especially in test environments, since the defaults don't get properly
    erase sometimes.

    TODO: Make tests better maybe so this is no problem anymore?

    Args:
        app (Eve object): The app to extend
        domain (dict): The domain to be added to the app, will not be changed
    """
    domain_copy = deepcopy(domain)

    for resource, settings in domain_copy.items():
        app.register_resource(resource, settings)


def register_validator(app, validator_class):
    """Extend the validator of the app.

    This creates a new validator class with both the new and old validato
    classes as parents and replaces the old validator class with the result.
    Since the validator has new parents it is called 'Adopted' ;)

    Using type with three arguments does just this.

    Args:
        app (Eve object): The app to extend
        validator_class: The class to add to the validaot
    """
    app.validator = type("Adopted_%s" % validator_class.__name__,
                         (validator_class, app.validator),
                         {})
# db utils


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
        r"""Make own class available to models.

        This makes it possible to reference fields indirectly with
        User.__self__.sessions. We use this as a workaround, as the lookup dict
        for eve can not contain sqlalchemy operators for a relation.

            { "sessions": "indirect_any(\"token\")" }

        This would fail cause eve_sqlalchemy first checks wether sessions is a
        relation and therefore never reaches the custom operator clause.

            { "__self__": "indirect_any(\"sessions.token\")" }

        This works as __self__ is not a relation.
        """
        return cls

    @classmethod
    def indirect_any(cls, querystring):
        r"""Check if any field is matched over various relations.

        This is used to check indirect permissions in authorization.py

        When the parser hits one to many relations it will create any clauses

        Example:
            User.recursive_any("groups.addresses.address, \"it@amiv.ethz.ch\"")

            this will return all users, which are in a group which receives
            emails from it@amiv.ethz.ch

        @argument querystring: String of two comma seperated arguments. The
                               first is the field which is to be checked. The
                               second is the value to match.

        @returns: sqlalchemy statement
        """
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
