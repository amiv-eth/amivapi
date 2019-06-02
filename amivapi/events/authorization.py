# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Authorization for events and eventsignups resources"""

from bson import ObjectId

from flask import g, current_app
from datetime import datetime as dt, timezone
from amivapi.auth import AmivTokenAuth
from amivapi.utils import get_id


class EventAuth(AmivTokenAuth):
    """Auth for events."""

    def has_item_write_permission(self, user_id, item):
        """The group moderator is allowed to change things."""
        # Return true if a moderator exists and it is equal to the current user
        return item.get('moderator') and (
                user_id == str(get_id(item['moderator'])))


class EventSignupAuth(AmivTokenAuth):
    def create_user_lookup_filter(self, user_id):
        """Users can see own signups and signups for moderated events.
        """
        # Find events the user moderates
        event_collection = current_app.data.driver.db['events']
        events = event_collection.find({'moderator': ObjectId(user_id)},
                                       {'_id': 1})
        moderated_events = [event['_id'] for event in events]

        return {'$or': [
            {'user': user_id},
            {'event': {'$in': moderated_events}}
        ]}

    def has_item_write_permission(self, user_id, item):
        """Users can modify their signups within the registration window.
            Moderators can not modify signups from other users.
        """
        if isinstance(item['event'], dict):
            event = item['event']
        else:
            # Event is not embedded, get the event first
            lookup = {current_app.config['ID_FIELD']: item['event']}
            event = current_app.data.find_one('events', None, **lookup)

        # Remove tzinfo to compare to utcnow (API only accepts UTC anyways)
        register_start = event['time_register_start']
        register_end = event['time_register_end']

        # Only the user itself can modify the item (not moderators), and only
        # within the signup window
        return (('user' in item) and
                (user_id == str(get_id(item['user']))) and
                (register_start <= dt.now(timezone.utc) <= register_end))

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
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled:
            if g.resource_admin or value is None:
                return
            if g.get('current_user') != str(value):
                self._error(field, "You can only enroll yourself. (%s: "
                                   "%s is yours)." % (field, g.current_user))
