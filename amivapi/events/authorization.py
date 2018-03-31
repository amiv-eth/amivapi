# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Authorization for events and eventsignups resources"""

from bson import ObjectId
from flask import g

from amivapi.auth import AmivTokenAuth


class EventSignupAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id: str) -> dict:
        """Make only own signups visible"""
        return {'user': user_id}

    def has_item_write_permission(self, user_id: str, item: dict) -> bool:
        """Users can only see their own signups, so they may change all visible
        signups"""
        return True

    def has_resource_write_permission(self, user_id: str) -> bool:
        """Anyone can sign up. Further requirements are enforced with validators
        to allow precise error messages.

        Users may only sign themselves up and anyone may POST with an email
        address.
        """
        return True


class EventAuthValidator(object):
    """ Custom validator to check permissions for events. """

    def _validate_only_self_enrollment_for_event(self, enabled: bool,
                                                 field: str,
                                                 value: ObjectId) -> None:
        """Validate if the user can be used to enroll for an event.

        1.  Anyone can signup with no user id
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource admins: they can sign up others as well

        Args:
            enabled: validates nothing if set to false
            field: field name.
            value: field value.
        """
        if enabled:
            if g.resource_admin or value is None:
                return
            if g.get('current_user') != str(value):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.current_user))
