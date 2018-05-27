# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event module.

Contains settings for eve resource, special validation and email_confirmation
logic needed for signup of non members to events.
"""


from amivapi.events.authorization import EventAuthValidator
from amivapi.events.emails import (
    add_confirmed_before_insert,
    email_blueprint,
    send_confirmmail_to_unregistered_users,
)
from amivapi.events.model import eventdomain
from amivapi.events.projections import (
    add_email_to_signup,
    add_email_to_signup_collection,
    add_position_to_signup,
    add_position_to_signup_collection,
    add_signup_count_to_event,
    add_signup_count_to_event_collection
)
from amivapi.events.queue import (
    add_accepted_before_insert,
    update_waiting_list_after_delete,
    update_waiting_list_after_insert,
)
from amivapi.events.validation import EventValidator
from amivapi.events.utils import create_token_secret_on_startup
from amivapi.utils import register_domain, register_validator


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    create_token_secret_on_startup(app)

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
    app.on_insert_eventsignups += add_confirmed_before_insert
    # Sending confirmation mails
    app.on_inserted_eventsignups += send_confirmmail_to_unregistered_users

    # Auto accept registrations for fcfs system
    app.on_insert_eventsignups += add_accepted_before_insert

    # Update waiting list after insert or delete of signups
    app.on_inserted_eventsignups += update_waiting_list_after_insert
    app.on_deleted_item_eventsignups += update_waiting_list_after_delete

    app.register_blueprint(email_blueprint)
