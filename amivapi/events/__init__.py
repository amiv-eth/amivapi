# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event module.

Contains settings for eve resource, special validation and email_confirmation
logic needed for signup of non members to events.
"""

from amivapi.utils import register_domain, register_validator

from .endpoints import eventdomain

from .projections import (
    add_email_to_signup,
    add_email_to_signup_collection,
    add_signup_count_to_event,
    add_signup_count_to_event_collection
)
from .validation import EventValidator
from .email_confirmations import (
    confirmprint,
    send_confirmmail_to_unregistered_users,
    send_confirmmail_to_unregistered_users_bulk,
    add_confirmed_before_insert,
    add_confirmed_before_insert_bulk
)


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, eventdomain)
    register_validator(app, EventValidator)

    # Show user's email in registered signups
    app.on_fetched_resource_eventsignups += add_email_to_signup_collection
    app.on_fetched_item_eventsignups += add_email_to_signup

    # Show signup count in events
    app.on_fetched_resource_events += add_signup_count_to_event_collection
    app.on_fetched_item_events += add_signup_count_to_event

    # Add confirmed field to incoming signups
    app.on_insert_item_eventsignups += add_confirmed_before_insert
    app.on_insert_eventsignups += add_confirmed_before_insert_bulk
    # Sending confirmation mails
    app.on_inserted_item_eventsignups += send_confirmmail_to_unregistered_users
    app.on_inserted_eventsignups += send_confirmmail_to_unregistered_users_bulk

    app.register_blueprint(confirmprint)
