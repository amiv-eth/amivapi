# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities."""


import smtplib
from email.mime.text import MIMEText
from copy import deepcopy
from contextlib import contextmanager

from flask import Config, request, g, current_app as app
from eve.utils import config
from eve.io.mongo import Validator

from amivapi.settings import ROOT_DIR


@contextmanager
def admin_permissions():
    """Switch to a context with admin rights and restore state afterwards.

    Use as context:
    >> with admin_rights():
    >>     do_something()
    """
    old_admin = g.get('resource_admin')
    g.resource_admin = True
    app.logger.debug("Overwriting g.resource_admin with True.")

    yield

    app.logger.debug("Restoring g.resource_admin.")
    if old_admin is not None:  # None means it wasn't set before..
        g.resource_admin = old_admin


def get_config():
    """Load the config from settings.py and updates it with config.cfg.

    :returns: Config dictionary
    """
    config = Config(ROOT_DIR)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("mongo_config.cfg")
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                      "`python manage.py create_config`.")

    return config


def mail(sender, to, subject, text):
    """Send a mail to a list of recipients.

    Args:
        from(string): From address
        to(list of strings): List of recipient addresses
        subject(string): Subject string
        text(string): Mail content
    """
    if app.config.get('TESTING', False):
        app.test_mails.append({
            'subject': subject,
            'from': sender,
            'receivers': to,
            'text': text
        })
    else:
        msg = MIMEText(text)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ';'.join(to)

        try:
            s = smtplib.SMTP(config.SMTP_SERVER)
            try:
                s.sendmail(msg['From'], to, msg.as_string())
            except smtplib.SMTPRecipientsRefused as e:
                app.logger.error(
                    "Failed to send mail:\nFrom: %s\nTo: %s\nSubject: %s\n\n%s"
                    % (sender, str(to), subject, text))
            s.quit()
        except smtplib.SMTPException as e:
            app.logger.error("SMTP error trying to send mails: %s" % e)


class ValidatorAMIV(Validator):
    """Validator subclass adding more validation for special fields."""

    def _validate_not_patchable(self, enabled, field, value):
        """Custom Validator to inhibit patching of the field.

        e.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled (bool): Boolean, should be true
            field (string): field name.
            value: field value.
        """
        if enabled and (request.method == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_not_patchable_unless_admin(self, enabled, field, value):
        """Inhibit patching of the field.

        e.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled (bool): Boolean, should be true
            field (string): field name.
            value: field value.
        """
        if enabled and (request.method == 'PATCH') and not g.resource_admin:
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
        patch = (request.method == 'PATCH')
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
