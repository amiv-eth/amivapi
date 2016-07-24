# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module initialization."""

from amivapi.utils import register_domain

from .model import userdomain, prevent_projection
from .security import hash_on_insert, hash_on_update


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, userdomain)

    app.on_pre_GET_users += prevent_projection
    app.on_insert_users += hash_on_insert
    app.on_update_users += hash_on_update
    app.on_replace_user += hash_on_update
