# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Logic to send emails on blacklist changes.

Send emails to users when they have a new entry on the blacklist or one of their
entries get resolved/deleted.
"""

from flask import current_app

from amivapi.utils import mail
from datetime import datetime, timezone, timedelta

from amivapi.cron import (
    schedulable,
    schedule_task
)


def _get_email(item):
    """Retrieve the user email for a blacklist entry."""
    id_field = current_app.config['ID_FIELD']
    lookup = {id_field: item['user']}
    user = current_app.data.find_one('users', None, **lookup)
    return user['email']


def schedule_email(item):
    """schedules an email when end_time is reached"""

    email = _get_email(item)
    fields = {'reason': item['reason']}
    schedule_task(item['end_time'], send_scheduled_email, email,
                  'Your blacklist entry has been removed!',
                  current_app.config['BLACKLIST_REMOVED'].format(**fields),
                  item['end_time'])


@schedulable
def send_scheduled_email(email, subject, message, blacklist_id):
    """Sends a scheduled email to a user whose entry has been deleted"""
    blacklist = current_app.data.find_one('blacklist', None,
                                          {"_id": blacklist_id})

    if (blacklist and blacklist['end_time'] and
       abs(blacklist['end_time']-datetime.now(timezone.utc))
       < timedelta(hours=4)):
        mail(email, subject, message)


def notify_new_blacklist(items):
    """Send an email to a user who has a new blacklist entry."""
    for item in items:
        email = _get_email(item)
        fields = {
            'reason': item['reason'],
            'reply_to': current_app.config['BLACKLIST_REPLY_TO']
        }

        if item['price']:
            fields['price'] = item['price']/100  # convert Rappen to CHF
            template = current_app.config['BLACKLIST_ADDED_EMAIL_W_PRICE']
        else:
            template = current_app.config['BLACKLIST_ADDED_EMAIL_WO_PRICE']

        mail(email, 'You have been blacklisted!', template.format(**fields))
        if item['end_time'] and item['end_time'] > datetime.utcnow():
            schedule_email(item)


def notify_patch_blacklist(new, old):
    """Send an email to a user if one of his entries was updated."""

    # Checks if the particular update resolved the blacklist entry or just
    # fixes an error, for example changed the reason or price. An entry is
    # resolved when the end_time is before now.
    if ('end_time' in new and new['end_time'] <= datetime.utcnow()):
        email = _get_email(new)
        fields = {'reason': new['reason']}

        mail(email, 'Your blacklist entry has been removed!',
             current_app.config['BLACKLIST_REMOVED'].format(**fields))

    if ('end_time' in new and
       ('end_time' not in old or old['end_time'] != new['end_time']) and
       new['end_time'] > datetime.utcnow()):
        schedule_email(new)


def notify_delete_blacklist(item):
    """Send an email to a user if one of his entries was deleted."""
    email = _get_email(item)
    fields = {'reason': item['reason']}

    mail(email, 'Your blacklist entry has been removed!',
         current_app.config['BLACKLIST_REMOVED'].format(**fields))
