import datetime as dt
from os.path import abspath, join
import json
from base64 import b64encode, b64decode
import hashlib
from os import urandom

from eve.utils import config
from flask import Config

from amivapi.settings import ROOT_DIR


def get_config(environment):
    """Load the config associated with <environment>. The config is loaded
    from config/<environment>.cfg

    :param environment: Name of the environment, should be 'development',
                        'testing' or 'production'
    :returns: Config dictionary
    """
    config_dir = abspath(join(ROOT_DIR, "config"))
    config = Config(config_dir)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("%s.cfg" % environment)
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                             + "`python manage.py create_config`.")

    return config


class DateTimeDecoder(json.JSONDecoder):
    """see DateTimeEncoder below"""

    def __init__(self, *args, **kargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.dict_to_object,
            *args, **kargs
        )

    def dict_to_object(self, d):
        if '__type__' not in d:
            return d

        type = d.pop('__type__')
        try:
            dateobj = dt(**d)
            return dateobj
        except:
            d['__type__'] = type
            return d


class DateTimeEncoder(json.JSONEncoder):
    """ Instead of letting the default encoder convert datetime to string,
        convert datetime objects into a dict, which can be decoded by the
        DateTimeDecoder
        We need this Converter to store the request in the Confirmation table
    """

    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return {
                '__type__': 'datetime',
                'year': obj.year,
                'month': obj.month,
                'day': obj.day,
                'hour': obj.hour,
                'minute': obj.minute,
                'second': obj.second,
                'microsecond': obj.microsecond,
            }
        else:
            return json.JSONEncoder.default(self, obj)


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
    :returns: String containing the salt and the hashed password
    """
    salt = urandom(16)
    password = bytearray(password, 'utf-8')
    return (
        b64encode(salt) +
        '$' +
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
