# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Auth and session endpoint."""

from amivapi.utils import register_domain

from endpoints import make_sessiondomain, Session
from . import authentication, authorization


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_sessiondomain())

    app.on_insert += authentication.set_author_on_insert
    app.on_replace += authentication.set_author_on_replace
    app.on_insert_sessions += authentication.process_login

    app.on_pre_GET += authorization.pre_get_permission_filter
    app.on_pre_POST += authorization.pre_post_permission_filter
    app.on_pre_PUT += authorization.pre_put_permission_filter
    app.on_pre_DELETE += authorization.pre_delete_permission_filter
    app.on_pre_PATCH += authorization.pre_patch_permission_filter
    app.on_pre_GET_groups += authorization.group_visibility_filter

    app.on_pre_GET_users += authorization.pre_users_get
