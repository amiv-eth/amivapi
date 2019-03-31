# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Logic to implement different signup queues."""

from flask import current_app
from pymongo import ASCENDING

from amivapi.events.emails import notify_signup_accepted


def update_waiting_list(event_id):
    """Fill up missing people in an event with people from the waiting list.
    This gets triggered by different hooks, whenever the list needs to be
    updated.

    1. After a new signup is created.
    2. After a signup was deleted.
    3. After an external signup was confirmed.

    Returns:
        list: ids of all singups which are newly accepted.
    """
    id_field = current_app.config['ID_FIELD']
    lookup = {id_field: event_id}
    event = current_app.data.find_one('events', None, **lookup)

    accepted_ids = []

    if event['selection_strategy'] == 'fcfs':
        lookup = {'event': event_id, 'accepted': True}
        signup_count = (
            current_app.data.driver.db['eventsignups'].count_documents(lookup))

        # 0 spots == infinite spots
        if event['spots'] == 0 or signup_count < event['spots']:
            lookup = {'event': event_id, 'accepted': False, 'confirmed': True}
            new_list = current_app.data.driver.db['eventsignups'].find(
                lookup).sort('_created', ASCENDING)

            if event['spots'] > 0:
                to_accept = new_list.limit(event['spots'] - signup_count)
            else:
                # infinite spots, so just accept everyone
                to_accept = new_list

            for new_accepted in to_accept:
                accepted_ids.append(new_accepted['_id'])
                # Set accepted flag
                current_app.data.update('eventsignups', new_accepted[id_field],
                                        {'accepted': True}, new_accepted)

                # Notify user
                notify_signup_accepted(event, new_accepted)

    return accepted_ids


"""
Hooks that trigger fcfs execution
"""


def add_accepted_before_insert(signups):
    """Add the accepted field before inserting signups."""
    for signup in signups:
        signup['accepted'] = False


def update_waiting_list_after_insert(signups):
    """Hook to automatically update the waiting list.

    Users get auto-accepted when fcfs is used and the event is not full yet.
    Update the response data if the signup got accepted.

    This could be optimized if multiple signups are for the same event,
    however we do not know that, so this just loop over them and calls the hook
    for each item.
    """
    for signup in signups:
        accepted = update_waiting_list(signup['event'])
        if signup['_id'] in accepted:
            signup['accepted'] = True


def update_waiting_list_after_delete(signup):
    """Hook to update the event waiting list after a signup is deleted."""
    if not signup['accepted']:
        # User was on the waitinglist, so nothing changes
        return

    update_waiting_list(signup['event'])
