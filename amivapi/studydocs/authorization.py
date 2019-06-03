# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Auth rules for studydocuments
"""

from flask import g

from amivapi.auth import AmivTokenAuth
from amivapi.utils import get_id


class StudydocsAuth(AmivTokenAuth):
    def has_item_write_permission(self, user_id, item):
        return str(get_id(item['uploader'])) == user_id

    def has_resource_write_permission(self, user_id):
        # All users can create studydocs
        return True


def add_uploader_on_insert(items):
    """Add the _author field before inserting studydocs"""
    for item in items:
        item['uploader'] = g.get('current_user')
