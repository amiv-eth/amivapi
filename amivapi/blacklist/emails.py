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
from datetime import datetime

from amivapi.cron import schedulable, schedule_task


def _get_email(item):
    """Retrieve the user email for a blacklist entry."""
    id_field = current_app.config['ID_FIELD']
    lookup = {id_field: item['user']}
    user = current_app.data.find_one('users', None, **lookup)
    return user['email']


@schedulable
def send_removed_mail(item):
    """Sends a scheduled email when end_time is reached and the entry is removed."""
    _item = current_app.data.find_one('blacklist', None, {"_id": item['_id']})
    # Check that the end date is still correct and has not changed again
    if _item is None:
        return  # Entry was deleted, no mail to send anymore
    if _item.get('end_time') is None:
        return  # Entry was patched to last indefinitely, so no mail to send.
    if _item['end_time'].replace(tzinfo=None) != item['end_time']
        return  # Entry was edited, so this is outdated.

    email = _get_email(_item)
    fields = {'reason': _item['reason']}
    mail(email,
         'Your blacklist entry has been removed!',
         current_app.config['BLACKLIST_REMOVED'].format(**fields))


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

        # If the end time is already known, schedule removal mail
        if item['end_time'] and item['end_time'] > datetime.utcnow():
            schedule_task(item['end_time'], send_removed_mail, item)


def notify_patch_blacklist(new, old):
    """Send an email to a user if one of his entries was updated."""
    # Checks if the particular update resolved the blacklist entry or just
    # fixes an error, for example changed the reason or price. An entry is
    # resolved when the end_time is before now. The end_time might also
    # have been removed, in which case we don't schedule an email either.
    if 'end_time' not in new or new['end_time'] is None:
        return

    # Either send mail immediately, or schedule for the future
    item = {**old, **new}
    if new['end_time'] <= datetime.utcnow():
        send_removed_mail(item)
    elif new['end_time'] != old['end_time']:
        schedule_task(new['end_time'], send_removed_mail, item)


def notify_delete_blacklist(item):
    """Send an email to a user if one of his entries was deleted."""
    email = _get_email(item)
    fields = {'reason': item['reason']}

    mail(email, 'Your blacklist entry has been removed!',
         current_app.config['BLACKLIST_REMOVED'].format(**fields))
