# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Group module.

Contains settings for eve resource, special validation.
Also contains email management for group mailing lists

And provides a helper function to check group permissions.
"""

from amivapi.utils import register_domain, register_validator

from .mailing_lists import (
    new_groups,
    new_members,
    removed_group,
    removed_member,
    updated_group,
    updated_user)
from .model import groupdomain
from .permissions import check_group_permissions
from .validation import GroupValidator


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, groupdomain)
    register_validator(app, GroupValidator)

    # authentication
    app.after_auth += check_group_permissions

    # email lists
    app.on_inserted_groups += new_groups
    app.on_updated_groups += updated_group
    app.on_deleted_item_groups += removed_group

    app.on_inserted_groupmemberships += new_members
    app.on_deleted_item_groupmemberships += removed_member

    app.on_updated_users += updated_user
