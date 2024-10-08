# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module initialization."""

from amivapi.utils import register_domain

from .model import userdomain
from .security import (
    hash_on_insert,
    hash_on_update,
    hide_after_request,
    hide_fields,
    project_password_status,
    project_password_status_on_inserted,
    project_password_status_on_updated,
    restrict_filters,
)
from .subscriberlist import init_subscriber_list
from .usersync import init_user_sync


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, userdomain)

    # Dynamically restrict filter
    app.on_pre_GET_users += restrict_filters

    # project_password_status must be before hide_fields
    app.on_fetched_item_users += project_password_status
    app.on_fetched_resource_users += project_password_status
    app.on_insert_users += hash_on_insert
    app.on_inserted_users += project_password_status_on_inserted
    app.on_update_users += hash_on_update
    app.on_updated_users += project_password_status_on_updated
    app.on_replace_user += hash_on_update
    app.on_replaced_user += project_password_status_on_updated

    # on_post_METHOD, triggered before sending the response by Eve
    for method in ['GET', 'POST', 'PATCH']:
        event = getattr(app, 'on_post_%s_users' % method)
        event += hide_after_request

    app.on_fetched_item_users += hide_fields

    init_subscriber_list(app)
    init_user_sync(app)
