# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Blacklist module.

Contains settings for eve resource, special validation.
"""

from amivapi.blacklist.model import blacklist
from amivapi.utils import register_domain


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, blacklist)
