# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Auth and session endpoint initialization."""
from amivapi.auth import apikeys, oauth
from amivapi.auth.auth import (
    abort_if_not_public,
    add_lookup_filter,
    AmivTokenAuth,
    authenticate,
    check_if_admin,
    check_item_write_permission,
    check_resource_write_permission
)
from amivapi.auth.link_methods import (
    add_permitted_methods_after_fetch_item,
    add_permitted_methods_after_fetch_resource,
    add_permitted_methods_after_insert,
    add_permitted_methods_after_update,
    add_permitted_methods_for_home
)
from amivapi.auth.sessions import process_login, sessiondomain
from amivapi.utils import register_domain


def init_app(app):
    """Register sessions resource, add auth and hooks."""
    # Auth
    app.auth = AmivTokenAuth()

    # Sessions
    register_domain(app, sessiondomain)
    app.on_insert_sessions += process_login

    # on_pre_METHOD, triggered right after auth by Eve
    for method in ['GET', 'POST', 'PATCH', 'DELETE']:
        event = getattr(app, 'on_pre_' + method)

        # Authentication and public method checking for all methods
        event += authenticate
        event += check_if_admin
        event += abort_if_not_public

        # Lookup filter for GET, PATCH, DELETE
        if method != 'POST':
            event += add_lookup_filter

    # Check resource write permission for POST and DELETE
    app.on_pre_POST += check_resource_write_permission
    app.on_delete_resource += check_resource_write_permission

    # Check item write permission for PATCH and DELETE
    app.on_update += (lambda resource, updates, original:
                      check_item_write_permission(resource, original))
    app.on_delete_item += check_item_write_permission

    # Add allowed methods
    app.on_inserted += add_permitted_methods_after_insert
    app.on_fetched_item += add_permitted_methods_after_fetch_item
    app.on_fetched_resource += add_permitted_methods_after_fetch_resource
    app.on_post_GET += add_permitted_methods_for_home
    app.on_post_PATCH += add_permitted_methods_after_update

    # Add apikey authorization
    apikeys.init_apikeys(app)
    oauth.init_oauth(app)
