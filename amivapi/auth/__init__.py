# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Auth and session endpoint initialization."""

from amivapi.utils import register_domain

from .sessions import sessiondomain, process_login
from .auth import (
    AmivTokenAuth,
    authenticate,
    abort_if_not_public,
    add_lookup_filter,
    check_write_permission
)
from .link_methods import (
    add_permitted_methods_after_update,
    add_permitted_methods_after_insert,
    add_permitted_methods_after_fetch_item,
    add_permitted_methods_after_fetch_resource,
    add_permitted_methods_for_home
)


def init_app(app):
    """Register sessions resource, add auth and hooks."""
    # Auth
    app.auth = AmivTokenAuth()  # Important that its an instance for "/"

    # Sessions
    register_domain(app, sessiondomain)
    app.on_insert_sessions += process_login

    # Hooks
    # on_pre_METHOD, triggered right after auth by Eve
    for method in ['GET', 'POST', 'PATCH', 'DELETE']:
        event = getattr(app, 'on_pre_' + method)

        # Authentication and public method checking for all methods
        event += authenticate
        event += abort_if_not_public

        # Lookup filter für GET, PATCH, DELETE
        if method != 'POST':
            event += add_lookup_filter

    # on_action hooks
    # Check write permission for PATCH and DELETE
    app.on_update += (lambda resource, updates, original:
                      check_write_permission(resource, original))
    app.on_delete_item += check_write_permission

    # Add allowed methods
    app.on_inserted += add_permitted_methods_after_insert
    app.on_updated += add_permitted_methods_after_update
    app.on_fetched_item += add_permitted_methods_after_fetch_item
    app.on_fetched_resource += add_permitted_methods_after_fetch_resource
    app.on_post_GET += add_permitted_methods_for_home
