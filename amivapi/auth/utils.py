# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities for auth module."""

from base64 import b64encode
from os import urandom


def gen_safe_token():
    """Cryptographically random generate a token that can be passed in a URL.
    The token is created from 256 random bits.

    Returns:
        str: A random string containing only urlsafe characters.
    """
    return b64encode(urandom(32)).decode("utf-8").replace("+", "-").replace(
        "/", "_")
