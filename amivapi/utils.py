from base64 import b64encode, b64decode
import hashlib
from os import urandom
import re
import string
import random

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


def create_new_hash(password):
    """Creates a new salted hash for a password. This generates a random salt,
    so it can not be used to check hashes!

    :param password: The password to hash
    :returns: Bytearray containing the salt and the hashed password
    """
    salt = urandom(16)
    password = bytearray(password, 'utf-8')
    return (
        b64encode(salt) +
        b'$' +
        b64encode(hashlib.pbkdf2_hmac('SHA256', password, salt, 100000))
    )


def check_hash(password, hash):
    """ Check a password against a string containing salt and hash generated
    by create_new_hash()

    :param password: The password to check
    :param hash: The string containing hash and salt to check against
    :returns: True if hash was generated with the same password, else False
    """
    parts = hash.split('$')
    salt = b64decode(parts[0])
    hashed_password = b64decode(parts[1])

    if hashed_password == hashlib.pbkdf2_hmac(
            'SHA256',
            bytearray(password, 'utf-8'),
            salt,
            100000
    ):
        return True
    return False


def token_generator(size=6, chars=string.ascii_letters + string.digits):
    """generates a random string of elements of chars
    :param size: length of the token
    :param chars: list of possible chars
    :returns: a random token
    """
    return ''.join(random.choice(chars) for _ in range(size))


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
