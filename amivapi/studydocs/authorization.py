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


class StudydocratingsAuth(AmivTokenAuth):
    def has_item_write_permission(self, user_id, item):
        """Allow users to modify only their own ratings."""
        # item['user'] is Objectid, convert to str
        return user_id == str(get_id(item['user']))

    def create_user_lookup_filter(self, user_id):
        """Allow users to only see their own ratings."""
        return {'user': user_id}

    def has_resource_write_permission(self, user_id):
        # All users can rate studydocs
        return True


def add_uploader_on_insert(items):
    """Add the _author field before inserting studydocs"""
    for item in items:
        item['uploader'] = g.get('current_user')
