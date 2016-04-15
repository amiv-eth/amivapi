# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event module.

Contains settings for eve resource, special validation and email_confirmation
logic needed for signup of non members to events.
"""

from amivapi.utils import register_domain, register_validator

from .settings import make_eventdomain, Event, EventSignup
from .validation import EventValidator
from . import email_confirmations as mail


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_eventdomain())
    register_validator(app, EventValidator)

    app.register_blueprint(mail.confirmprint)

    # Hooks for anonymous users
    app.on_insert_eventsignups += mail.signups_confirm_anonymous

    app.on_update += mail.pre_update_confirmation
    app.on_delete_item += mail.pre_delete_confirmation
    app.on_replace += mail.pre_replace_confirmation

    # Hooks to move 'email' to '_unregistered_email' after db access
    app.on_insert_eventsignups += mail.replace_email_insert
    app.on_update_eventsignups += mail.replace_email_update
    app.on_replace_eventsignups += mail.replace_email_replace

    # Hooks to move '_unregistered_email' to 'email' after db access
    app.on_inserted_eventsignups += mail.replace_email_inserted
    app.on_fetched_item_eventsignups += mail.replace_email_fetched_item
    app.on_fetched_resource_eventsignups += mail.replace_email_fetched_resource
    app.on_replaced_eventsignups += mail.replace_email_replaced
    app.on_updated_eventsignups += mail.replace_email_updated

    # Hooks to remove tokens from output
    app.on_inserted_eventsignups += mail.remove_token_inserted
    app.on_fetched_item_eventsignups += mail.remove_token_fetched_item
    app.on_fetched_resource_eventsignups += mail.remove_token_fetched_resource
    app.on_replaced_eventsignups += mail.remove_token_replaced
