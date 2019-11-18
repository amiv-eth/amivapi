# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Logic to implement different signup queues."""

from datetime import datetime, timedelta
from random import sample
import pytz

from flask import current_app, url_for
from itsdangerous import URLSafeSerializer
from pymongo import ASCENDING

from amivapi.utils import mail
from amivapi.events.utils import get_token_secret
from amivapi.cron import schedule_task


# @schedulable
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

    accepted_signups = []
    if event['selection_strategy'] != 'fcfs':
        return []

    signup_count = current_app.data.driver.db['eventsignups'].find(
        {'event': event_id}).count_documents()
    accepted_count = current_app.data.driver.db['eventsignups'].find(
        {'event': event_id, 'accepted': True}).count_documents()

    if event['spots'] != 0:
        # Fair FCFS Lottery
        lottery_deadline = event['time_register_start'] + timedelta(minutes=1)

        if lottery_deadline >= datetime.now(pytz.utc):
            if signup_count == 0:
                # This is the first signup, schedule an update of the waiting
                # list in 1 minute.
                schedule_task(datetime.now() + timedelta(minutes=2),
                              update_waiting_list, event_id)
            return []

        lottery_tickets = current_app.data.driver.db['eventsignups'].find(
            {'event': event_id,
             '_created': {'$lt': lottery_deadline},
             'accepted': False,
             'confirmed': True})
        num_lottery_tickets = lottery_tickets.count_documents()

        if num_lottery_tickets > 0 and event['spots'] - accepted_count > 0:
            winners = sample(range(num_lottery_tickets),
                             min(num_lottery_tickets,
                                 event['spots'] - accepted_count))
            accepted_signups.extend([lottery_tickets[i] for i in winners])
            accepted_count += len(winners)

    # FCFS for the rest
    # 0 spots == infinite spots
    if event['spots'] == 0 or accepted_count < event['spots']:
        lookup = {'event': event_id, 'accepted': False, 'confirmed': True}
        new_list = current_app.data.driver.db['eventsignups'].find(
            lookup).sort('_created', ASCENDING)

        if event['spots'] > 0:
            accepted_signups.extend(new_list.limit(
                event['spots'] - accepted_count))
        else:
            # infinite spots, so just accept everyone
            accepted_signups.extend(new_list)

    for signup in accepted_signups:
        # Set accepted flag
        current_app.data.update('eventsignups', signup[id_field],
                                {'accepted': True}, signup)
        # Notify user
        title = event.get('title_en') or event.get('title_de')
        notify_signup_accepted(title, signup)

    return [signup[id_field] for signup in accepted_signups]


def notify_signup_accepted(event_name, signup):
    """Send an email to a user, that his signup was accepted"""
    id_field = current_app.config['ID_FIELD']

    if signup.get('user'):
        lookup = {id_field: signup['user']}
        user = current_app.data.find_one('users', None, **lookup)
        name = user['firstname']
        email = user['email']
    else:
        name = 'Guest of AMIV'
        email = signup['email']

    s = URLSafeSerializer(get_token_secret())
    token = s.dumps(str(signup[id_field]))

    if current_app.config.get('SERVER_NAME') is None:
        current_app.logger.warning("SERVER_NAME is not set. E-Mail links "
                                   "will not work!")

    deletion_link = url_for('emails.on_delete_signup', token=token,
                            _external=True)

    mail(current_app.config['API_MAIL'], email,
         '[AMIV] Eventsignup accepted',
         'Hello %s!\n'
         '\n'
         'We are happy to inform you that your signup for %s was accepted and '
         'you can come to the event! If you do not have time to attend the '
         'event please click this link to free your spot for someone else:\n'
         '\n%s\n\n'
         'Best Regards,\n'
         'The AMIV event bot'
         % (name, event_name, deletion_link))


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
