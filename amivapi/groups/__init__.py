# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Group module.

Contains settings for eve resource, special validation.
Also contains email management for group mailing lists

And provides a helper function to check group permissions.
"""

from flask import current_app

from amivapi.utils import register_domain, register_validator

from .endpoints import (
    make_groupdomain,
    Group, GroupMember,
    GroupAddress,
    GroupForward
)
from .validation import GroupValidator, create_group_permissions_jsonschema
from . import mailing_lists as mail


def check_group_permission(user_id, resource, method):
    """Check group permissions of user.

    This function checks wether the user is permitted to access
    the given resource with the given method based on the groups
    he is in.

    :param user_id: the id of the user to check
    :param resource: the requested resource
    :param method: the used method

    :returns: Boolean, True if permitted, False otherwise
    """
    db = current_app.data.driver.session
    query = db.query(Group.permissions).filter(
        Group.members.any(GroupMember.user_id == user_id))

    # All entries are dictionaries
    # If any dicitionary contains the permission it is good.
    for row in query:
        if (row.permissions and
                (row.permissions.get(resource, {}).get(method, False))):
            return True

    return False


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_groupdomain())
    register_validator(app, GroupValidator)

    # email-management
    # Addresses
    app.on_inserted_groupaddresses += mail.create_files
    app.on_replaced_groupaddresses += mail.update_file
    app.on_updated_groupaddresses += mail.update_file
    app.on_deleted_item_groupaddresses += mail.delete_file
    # Members - can not be updated or replaced
    app.on_inserted_groupmembers += mail.add_user_email
    app.on_deleted_item_groupmembers += mail.remove_user_email
    # Forwards
    app.on_inserted_groupforwards += mail.add_forward_email
    app.on_replaced_groupforwards += mail.replace_forward_email
    app.on_updated_groupforwards += mail.update_forward_email
    app.on_deleted_item_groupforwards += mail.remove_forward_email
