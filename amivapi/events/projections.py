# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Hooks to generate fields in events and eventsignups"""

from flask import current_app


def add_email_to_signup(item):
    if 'email' not in item:
        if isinstance(item['user'], dict):
            # If user is embedded just copy the email
            item['email'] = item['user']['email']
        else:
            # User is not embedded, get the user and insert email
            lookup = {current_app.config['ID_FIELD']: item['user']}
            user = current_app.data.find_one('users', None, **lookup)
            item['email'] = user['email']


def add_email_to_signup_collection(response):
    for item in response['_items']:
        add_email_to_signup(item)


def add_signup_count_to_event(item):
    """After an event is fetched from the database we add the current signup
    count"""
    item['signup_count'] = current_app.data.driver.db['eventsignups'].find(
        {'event': item['_id']}).count()


def add_signup_count_to_event_collection(items):
    for item in items['_items']:
        add_signup_count_to_event(item)
