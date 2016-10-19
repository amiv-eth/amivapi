# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Authorization for events and eventsignups resources"""

from amivapi.auth import AmivTokenAuth


class EventSignupAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id):
        """Make only own signups visible"""
        return {'user': user_id}

    def has_item_write_permission(self, user_id, item):
        """Users can only see their own signups, so they may change all visible
        signups"""
        return True

    def has_resource_write_permission(self, user_id):
        """Anyone can sign up. Further requirements are enforced with validators
        to allow precise error messages.

        Users may only sign themselves up and anyone may POST with an email
        address.
        """
        return True
