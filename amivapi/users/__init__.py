# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module initialization."""
from eve import Eve

from amivapi.utils import register_domain

from .model import userdomain
from .security import (
    hash_on_insert,
    hash_on_update,
    hide_fields,
    project_password_status
)


def init_app(app: Eve) -> None:
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, userdomain)

    # project_password_status must be before hide_fields
    app.on_fetched_item_users += project_password_status
    app.on_fetched_resource_users += project_password_status
    app.on_fetched_item_users += hide_fields
    app.on_fetched_resource_users += hide_fields
    app.on_insert_users += hash_on_insert
    app.on_update_users += hash_on_update
    app.on_replace_user += hash_on_update
