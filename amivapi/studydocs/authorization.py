# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Auth rules for studydocuments
"""

from flask import request, g

from amivapi.auth import AmivTokenAuth


class StudydocsAuth(AmivTokenAuth):
    def has_item_write_permission(self, user_id, item):
        return str(item['_author']) == user_id

    def has_resource_write_permission(self, user_id):
        if request.method == 'POST':
            return True
        return False  # No delete on resource for users


def add_author_on_insert(item):
    """Add the _author field before inserting studydocs"""
    item['_author'] = g.current_user


def add_author_on_bulk_insert(items):
    for item in items:
        add_author_on_insert(item)
