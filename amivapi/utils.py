# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from base64 import urlsafe_b64encode
from os import urandom
import smtplib
from email.mime.text import MIMEText

from flask import current_app as app

from eve.utils import config
from flask import Config

from amivapi import models
from amivapi.settings import ROOT_DIR


def get_config():
    """Load the config from settings.py and updates it with config.cfg

    :returns: Config dictionary
    """
    config = Config(ROOT_DIR)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("config.cfg")
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                             + "`python manage.py create_config`.")

    return config


def get_class_for_resource(resource):
    """ Utility function to get SQL Alchemy model associated with a resource

    :param resource: Name of a resource
    :returns: SQLAlchemy model associated with the resource from models.py
    """
    if resource in config.DOMAIN:
        resource_def = config.DOMAIN[resource]
        return getattr(models, resource_def['datasource']['source'])

    if hasattr(models, resource.capitalize()):
        return getattr(models, resource.capitalize())

    return None


def token_generator(size=6):
    """generates a random string of elements of chars
    :param size: length of the token
    :returns: a random token
    """
    return urlsafe_b64encode(urandom(size))[0:size]


def recursive_any_getattr(obj, path):
    """ Given some object and a path, retrive any value, which is reached with
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
    """ will search for the owner(s) of a data-item
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
    """ Send a mail to a list of recipients

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


def check_group_permission(user_id, resource, method):
    """
        This function checks wether the user is permitted to access
        the given resource with the given method based on the groups
        he is in.

        :param user_id: the id of the user to check
        :param resource: the requested resource
        :param method: the used method

        :returns: Boolean, True if permitted, False otherwise
        """

    db = app.data.driver.session
    query = db.query(models.Group.permissions).filter(
        models.Group.members.any(models.GroupMember.user_id == user_id))

    # All entries are dictionaries
    # If any dicitionary contains the permission it is good.
    for row in query:
        if (row.permissions and
                (row.permissions.get(resource, {}).get(method, False))):
            return True

    return False
