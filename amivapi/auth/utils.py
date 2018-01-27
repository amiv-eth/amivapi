# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities for auth module."""

from base64 import b64encode
from os import urandom


def init_secret(app):
    """Get secret key from database or create it. Put in config.

    The secret key is stored in the database to ensure consistency.
    If no secret is in the database yet, create it.

    The database collection holding this key is called `config`.
    """
    with app.app_context():  # App context needed for db connection
        key = 'TOKEN_SECRET'  # Flask requires this name of the config entry
        db = app.data.driver.db['config']
        result = db.find_one({key: {'$exists': True, '$nin': [None, '']}})

        if result is not None:
            secret = result[key]
        else:
            # Create secret and save in db
            secret = b64encode(urandom(32)).decode('utf_8')
            db.insert_one({key: secret})

        app.config[key] = secret


def gen_safe_token():
    """Cryptographically random generate a token that can be passed in a URL.
    The token is created from 256 random bits.

    Returns:
        str: A random string containing only urlsafe characters.
    """
    return b64encode(urandom(32)).decode("utf-8").replace("+", "-").replace(
        "/", "_").rstrip("=")
