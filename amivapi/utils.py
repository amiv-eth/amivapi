# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from base64 import urlsafe_b64encode
from os import urandom
import re
import smtplib
from email.mime.text import MIMEText

from flask import current_app as app
from flask import abort

from eve.utils import config
from flask import Config

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


def get_class_for_resource(models, resource):
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


def get_owner(model, _id):
    """ will search for the owner(s) of a data-item
    :param modeL: the SQLAlchemy-model (in models.py)
    :param _id: The id of the item (unique for each model)
    :returns: a list of owner-ids
    """
    db = app.data.driver.session
    doc = db.query(model).get(_id)
    if not doc or not hasattr(model, '__owner__'):
        return None
    ret = []
    for path in doc.__owner__:
        attrs = re.split(r'\.', path)
        for attr in attrs:
            try:
                doc = getattr(doc, attr)
            except:
                abort(500, description=(
                    "Something is wrong with the data model."
                    " Please contact it@amiv.ethz.ch"))
        ret.append(doc)
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
