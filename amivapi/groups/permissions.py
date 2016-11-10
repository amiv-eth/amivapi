# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Permissions for group members."""

from bson import ObjectId

from flask import current_app, g


def check_group_permissions(resource):
    """do shit"""
    user = g.get('current_user')

    if user:
        # Find the users groups giving permission for a resource
        memberships = current_app.data.driver.db['groupmemberships'].find(
            {'user': ObjectId(user)}, {'group': 1})
        group_ids = [m['group'] for m in memberships]
        permission_key = 'permissions.%s' % resource
        groups = current_app.data.driver.db['groups'].find(
            {'_id': {'$in': group_ids}, permission_key: {'$exists': True}},
            {permission_key: 1})
        permissions = [group['permissions'][resource] for group in groups]

        if 'read' in permissions:
            g.resource_admin_readonly = True
        if 'readwrite' in permissions:
            g.resource_admin = True
