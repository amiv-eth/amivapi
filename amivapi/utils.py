# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities."""


from base64 import b64encode
from contextlib import contextmanager
from copy import deepcopy
from email.mime.text import MIMEText
from os import urandom
import smtplib
from functools import wraps
import json

from bson import ObjectId
from eve.utils import config
from flask import current_app as app
from flask import g


def token_urlsafe(nbytes=None):
    """Cryptographically random generate a token that can be passed in a URL.

    This function is available as secrets.token_urlsafe in python3.6. We can
    remove this function when we drop python3.5 support.

    Args:
        nbytes: Number of random bytes used to generate the token. Note that
        this is not the resulting length of the token, just the amount of
        randomness.

    Returns:
        str: A random string containing only urlsafe characters.
    """
    if nbytes is None:
        nbytes = 16

    return b64encode(urandom(nbytes)).decode("utf-8").replace("+", "-").replace(
        "/", "_").rstrip("=")


@contextmanager
def admin_permissions():
    """Switch to a context with admin rights and restore state afterwards.

    Use as context:
    >> with admin_rights():
    >>     do_something()
    """
    old_admin = g.get('resource_admin')
    g.resource_admin = True

    yield

    if old_admin is not None:  # None means it wasn't set before..
        g.resource_admin = old_admin


def get_id(item):
    """Get the id of a field in a relation. Depending on the embedding clause
    a field returned by a mongo query may be an ID or an object. This function
    will get the ID in both cases.

    Args:
        item: Either an object from the database as a dict or an object id as
            str or objectid.

    Returns:
        ObjectId with the user ID
    """
    try:
        return ObjectId(item)
    except TypeError:
        return ObjectId(item['_id'])


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
            with smtplib.SMTP(config.SMTP_SERVER,
                              port=config.SMTP_PORT,
                              timeout=config.SMTP_TIMEOUT) as smtp:
                status_code, _ = smtp.starttls()
                if status_code != 220:
                    app.logger.error("Failed to create secure "
                                     "SMTP connection!")
                    return

                if config.SMTP_USERNAME and config.SMTP_PASSWORD:
                    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                else:
                    smtp.ehlo()

                try:
                    smtp.sendmail(msg['From'], to, msg.as_string())
                except smtplib.SMTPRecipientsRefused as e:
                    error = ("Failed to send mail:\n"
                             "From: %s\nTo: %s\n"
                             "Subject: %s\n\n%s")
                    app.logger.error(error % (sender, str(to), subject, text))
        except smtplib.SMTPException as e:
            app.logger.error("SMTP error trying to send mails: %s" % e)


def run_embedded_hooks_fetched_item(resource, item):
    """Run fetched_* hooks on embedded objects. Eve doesn't execute hooks
    for those and we depend on it for auth and filtering of hidden fields.

    Args:
        resource: Name of the resource of the main request.
        item: Object including embedded objects.
    """
    # Find schema for all embedded fields
    schema = app.config['DOMAIN'][resource]['schema']
    embedded_fields = {field: field_schema
                       for field, field_schema in schema.items()
                       if 'data_relation' in field_schema}

    for field, field_schema in embedded_fields.items():
        rel_resource = field_schema['data_relation']['resource']
        # Call hooks on every embedded item in the response
        if field in item and isinstance(item[field], dict):
            getattr(app, "on_fetched_item")(rel_resource, item[field])
            getattr(app, "on_fetched_item_%s" % rel_resource)(item[field])


def run_embedded_hooks_fetched_resource(resource, response):
    """Run fetched hooks on embedded resources. Eve doesn't execute hooks
    for those and we depend on it for auth and filtering of hidden fields.

    Args:
        resource: Name of the resource of the main request.
        items: Objects including embedded objects.
    """
    for item in response['_items']:
        run_embedded_hooks_fetched_item(resource, item)


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


def on_post_hook(func):
    """Wrapper for an Eve `on_post_METHOD_resource` hook.

    The hook receives only a flask response object, which is difficult to
    manipulate.
    This wrapper extracts the data as dict and set the data again after the
    wrapped function has manipulated it.
    The function is only called for successful requests, otherwise there
    is no payload.

    The wrapped function can look like this:

        my_hook(payload):
            ...

    or, for hooks that don't specify the resource:

        my_hook(payload):
            ...
    """
    @wraps(func)
    def wrapped(*args):
        """This is the hook eve will see."""
        response = args[-1]
        if response.status_code in range(200, 300):
            payload = json.loads(response.get_data(as_text=True))
            func(*args, payload)
            response.set_data(json.dumps(payload))
    return wrapped
