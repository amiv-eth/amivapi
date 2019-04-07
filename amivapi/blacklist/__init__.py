# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Blacklist module.

Contains settings for eve resource, special validation.
"""

from amivapi.blacklist.model import blacklist
from amivapi.utils import register_domain

from amivapi.blacklist.emails import (
    notify_new_blacklist,
    notify_patch_blacklist,
    notify_delete_blacklist,
)


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, blacklist)

    # Send emails to users who have new/changed blacklist entries
    app.on_inserted_blacklist += notify_new_blacklist
    app.on_updated_blacklist += notify_patch_blacklist
    app.on_deleted_item_blacklist += notify_delete_blacklist
