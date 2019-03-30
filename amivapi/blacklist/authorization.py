# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Authorization for the blacklist resource."""

from amivapi.auth import AmivTokenAuth


class BlacklistAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id):
        """Users can see their own signups."""
        return {'user': user_id}

    def has_item_write_permission(self, user_id, item):
        """Only admins have right permission, but we don't
        have to care about them"""
        return False
