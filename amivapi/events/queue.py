# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Logic to implement different signup queues
"""

from flask import current_app, url_for
from itsdangerous import Signer
from pymongo import ASCENDING

from amivapi.utils import mail


def update_waiting_list(event_id):
    """Fill up missing people in an event with people from the waiting list.
    This gets triggered by different hooks, whenever the list needs to be
    updated.

    1. After a new signup is created.
    2. After a signup was deleted.
    3. After an external signup was confirmed.
    """
    id_field = current_app.config['ID_FIELD']
    lookup = {id_field: event_id}
    event = current_app.data.find_one('events', None, **lookup)

    if event['selection_strategy'] == 'fcfs':
        lookup = {'event': event_id, 'accepted': True}
        signup_count = current_app.data.driver.db['eventsignups'].find(
            lookup).count()

        if signup_count < event['spots']:
            lookup = {'event': event_id, 'accepted': False, 'confirmed': True}
            new_list = current_app.data.driver.db['eventsignups'].find(
                lookup).sort('_created', ASCENDING)

            for new_accepted in new_list.limit(event['spots'] - signup_count):
                # Set accepted flag
                current_app.data.update('eventsignups', new_accepted[id_field],
                                        {'accepted': True}, new_accepted)

                # Notify user
                title = event.get('title_en', event.get('title_de'))
                notify_signup_accepted(title, new_accepted)


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

    token = Signer(current_app.config['TOKEN_SECRET']).sign(
        str(signup[id_field]).encode('utf-8'))

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


def add_accepted_before_insert(signup):
    """Add the accepted field before inserting signups"""
    signup['accepted'] = False


def add_accepted_before_insert_collection(signups):
    """Trigger item hook in loop for collection"""
    for s in signups:
        add_accepted_before_insert(s)


def update_waiting_list_after_insert(signup):
    """Hook to automatically update the waiting list, when new signups are
    created. This way users get accepted, when fcfs is used and the event is not
    full yet."""
    update_waiting_list(signup['event'])


def update_waiting_list_after_insert_collection(signups):
    """Call the auto_accept_fcfs_signup hook for bulk inserts. This could be
    optimized if multiple signups are for the same event, however we do not
    know that, so this just loop over them and calls the hook for each item."""
    for s in signups:
        update_waiting_list_after_insert(s)


def update_waiting_list_after_delete(signup):
    """Hook, called when a signup was deleted, to update the waiting list of
    the associated event"""
    if not signup['accepted']:
        # User was on the waitinglist, so nothing changes
        return

    update_waiting_list(signup['event'])
