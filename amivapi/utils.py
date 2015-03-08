import datetime as dt
from os.path import abspath, join
import json
from base64 import b64encode, b64decode
import hashlib
from os import urandom

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from eve.utils import config
from flask import Config

from amivapi import models
from amivapi.settings import ROOT_DIR


def get_config(environment):
    config_dir = abspath(join(ROOT_DIR, "config"))
    config = Config(config_dir)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("%s.cfg" % environment)
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                             + "`python manage.py create_config`.")

    return config


def init_database(connection, config):
    try:
        models.Base.metadata.create_all(connection, checkfirst=False)
    except OperationalError:
        print("You are trying to create a new database, but the database " +
              "already exists!")
        raise

    session = Session(bind=connection)

    root = models.User(
        id=0,
        _author=0,
        _etag='d34db33f',  # We need some etag, not important what it is
        _created=dt.datetime.now(),
        _updated=dt.datetime.now(),
        username="root",
        password=create_new_hash(u"root"),
        firstname=u"Lord",
        lastname=u"Root",
        gender="male",
        email=config['ROOT_MAIL'],
        membership="none"
    )
    session.add(root)

    anonymous = models.User(
        id=-1,
        _author=0,
        _etag='4l3x15F4G',
        _created=dt.datetime.now(),
        _updated=dt.datetime.now(),
        username="anonymous",
        password=create_new_hash(u""),
        firstname=u"Anon",
        lastname=u"X",
        gender="male",
        email=u"nobody@example.com",
        membership="none"
    )
    session.add(anonymous)

    session.commit()


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


def get_class_for_resource(resource):
    """ Utility function to get SQL Alchemy model associated with a resource
    """
    if resource in config.DOMAIN:
        resource_def = config.DOMAIN[resource]
        return getattr(models, resource_def['datasource']['source'])

    if hasattr(models, resource.capitalize()):
        return getattr(models, resource.capitalize())

    return None


""" Creates a new hash for a password. This generates a random salt, so it can
not be used to check hashes!
"""


def create_new_hash(password):
    salt = urandom(16)
    password = bytearray(password, 'utf-8')
    return (
        b64encode(salt) +
        '$' +
        b64encode(hashlib.pbkdf2_hmac('SHA256', password, salt, 100000))
    )


def check_hash(password, hash):
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
