# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Logic to send emails on blacklist changes.

Send emails to users when they have a new entry on the blacklist or one of their
entries get resolved/deleted.
"""

from flask import current_app

from amivapi.utils import mail_from_template
from datetime import datetime

from amivapi.cron import schedulable, schedule_task


def _get_email_and_name(item):
    """Retrieve the user email for a blacklist entry."""
    id_field = current_app.config['ID_FIELD']
    lookup = {id_field: item['user']}
    user = current_app.data.find_one('users', None, **lookup)
    return user['email'], user['firstname']


@schedulable
def send_removed_mail(item):
    """Send scheduled email when a blacklist entry times out."""
    _item = current_app.data.find_one('blacklist', None, {"_id": item['_id']})
    # Check that the end date is still correct and has not changed again
    if _item is None:
        return  # Entry was deleted, no mail to send anymore
    if _item.get('end_time') is None:
        return  # Entry was patched to last indefinitely, so no mail to send.
    if _item['end_time'].replace(tzinfo=None) != item['end_time']:
        return  # Entry was edited, so this is outdated.

    email, name = _get_email_and_name(_item)
    fields = {'reason': _item['reason'], 'name': name}
    mail_from_template(
        to=email,
        subject='Your blacklist entry has been removed!',
        template_name='blacklist_removed',
        template_args=fields,
        reply_to=current_app.config['BLACKLIST_REPLY_TO'])


def notify_new_blacklist(items):
    """Send an email to a user who has a new blacklist entry."""
    for item in items:
        email, name = _get_email_and_name(item)
        fields = {
            'reason': item['reason'],
            'reply_to': current_app.config['BLACKLIST_REPLY_TO'],
            'name': name
        }

        if item['price']:
            fields['price'] = item['price']/100  # convert Rappen to CHF

        mail_from_template(
            to=email,
            subject='You have been blacklisted!',
            template_name='blacklist_added',
            template_args=fields,
            reply_to=current_app.config['BLACKLIST_REPLY_TO'])

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
    email, name = _get_email_and_name(item)
    fields = {'reason': item['reason'], 'name': name}

    mail_from_template(
        to=email,
        subject='Your blacklist entry has been removed!',
        template_name='blacklist_removed',
        template_args=fields,
        reply_to=current_app.config['BLACKLIST_REPLY_TO'])
