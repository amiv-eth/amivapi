# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Authorization for events and eventsignups resources"""

from flask import g, current_app
from datetime import datetime as dt
from amivapi.auth import AmivTokenAuth


class EventSignupAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id):
        """Make only own signups visible"""
        return {'user': user_id}

    def has_item_write_permission(self, user_id, item):
        """Users can only see their own signups. They may change their own
        signups only within the registration window of the event."""
        if isinstance(item['event'], dict):
            event = item['event']
        else:
            # Event is not embedded, get the event first
            lookup = {current_app.config['ID_FIELD']: item['event']}
            event = current_app.data.find_one('events', None, **lookup)

        return event['time_register_start'] <= dt.utcnow() <= event['time_register_end']

    def has_resource_write_permission(self, user_id):
        """Anyone can sign up. Further requirements are enforced with validators
        to allow precise error messages.

        Users may only sign themselves up and anyone may POST with an email
        address.
        """
        return True


class EventAuthValidator(object):
    """ Custom validator to check permissions for events. """

    def _validate_only_self_enrollment_for_event(self, enabled, field, value):
        """Validate if the user can be used to enroll for an event.

        1.  Anyone can signup with no user id
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource admins: they can sign up others as well

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            if g.resource_admin or value is None:
                return
            if g.get('current_user') != str(value):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.current_user))
