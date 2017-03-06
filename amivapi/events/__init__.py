# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event module.

Contains settings for eve resource, special validation and email_confirmation
logic needed for signup of non members to events.
"""

from amivapi.utils import register_domain, register_validator

from .model import eventdomain
from .authorization import EventAuthValidator
from .projections import (
    add_email_to_signup,
    add_email_to_signup_collection,
    add_position_to_signup,
    add_position_to_signup_collection,
    add_signup_count_to_event,
    add_signup_count_to_event_collection
)
from .validation import EventValidator
from .emails import (
    email_blueprint,
    send_confirmmail_to_unregistered_users,
    send_confirmmail_to_unregistered_users_bulk,
    add_confirmed_before_insert,
    add_confirmed_before_insert_bulk
)
from .queue import (
    add_accepted_before_insert,
    add_accepted_before_insert_collection,
    update_waiting_list_after_insert,
    update_waiting_list_after_insert_collection,
    update_waiting_list_after_delete
)


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, eventdomain)
    register_validator(app, EventValidator)
    register_validator(app, EventAuthValidator)

    # Show user's email in registered signups
    app.on_fetched_resource_eventsignups += add_email_to_signup_collection
    app.on_fetched_item_eventsignups += add_email_to_signup

    # Show user's position in the signup list
    app.on_fetched_resource_eventsignups += add_position_to_signup_collection
    app.on_fetched_item_eventsignups += add_position_to_signup

    # Show signup count in events
    app.on_fetched_resource_events += add_signup_count_to_event_collection
    app.on_fetched_item_events += add_signup_count_to_event

    # Add confirmed field to incoming signups
    app.on_insert_item_eventsignups += add_confirmed_before_insert
    app.on_insert_eventsignups += add_confirmed_before_insert_bulk
    # Sending confirmation mails
    app.on_inserted_item_eventsignups += send_confirmmail_to_unregistered_users
    app.on_inserted_eventsignups += send_confirmmail_to_unregistered_users_bulk

    # Auto accept registrations for fcfs system
    app.on_insert_item_eventsignups += add_accepted_before_insert
    app.on_insert_eventsignups += add_accepted_before_insert_collection

    # Update waiting list after insert or delete of signups
    app.on_inserted_item_eventsignups += update_waiting_list_after_insert
    app.on_inserted_eventsignups += update_waiting_list_after_insert_collection
    app.on_deleted_item_eventsignups += update_waiting_list_after_delete

    app.register_blueprint(email_blueprint)
