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


def notify_new_blacklist(items):
    """Send an email to a user who has a new blacklist entry."""

    for item in items:
        id_field = current_app.config['ID_FIELD']

        lookup = {id_field: item['user']}
        user = current_app.data.find_one('users', None, **lookup)
        email = user['email']

        fields = {
            'reason': item['reason'],
            'bouncermail': current_app.config['BLACKLIST_REPLY_TO']
        }

        if item['price']:
            fields['price'] = item['price']/100  # convert Rappen to CHF
            mail(current_app.config['API_MAIL'], email,
                 'You have been blacklisted!',
                 current_app.config['BLACKLIST_ADDED_EMAIL_W_PRICE'] % fields)
        else:
            mail(current_app.config['API_MAIL'], email,
                 'You have been blacklisted!',
                 current_app.config['BLACKLIST_ADDED_EMAIL_WO_PRICE'] % fields)


def notify_patch_blacklist(new, old):
    """Send an email to a user if one of his entries was updated."""

    # Checks if the particular update resolved the blacklist entry or just
    # fixes an error, for example changed the reason or price. An entry is
    # resolved when the end_time is before now.
    if ((not old['end_time']) and
            'end_time' in new and new['end_time'] <= datetime.utcnow()):
        id_field = current_app.config['ID_FIELD']

        lookup = {id_field: new['user']}
        user = current_app.data.find_one('users', None, **lookup)
        email = user['email']

        fields = {'reason': new['reason']}

        mail(current_app.config['API_MAIL'], email,
             'Your blacklist entry has been removed!',
             current_app.config['BLACKLIST_REMOVED'] % fields)


def notify_delete_blacklist(item):
    """Send an email to a user if one of his entries was deleted."""

    id_field = current_app.config['ID_FIELD']

    lookup = {id_field: item['user']}
    user = current_app.data.find_one('users', None, **lookup)
    email = user['email']

    fields = {'reason': item['reason']}

    mail(current_app.config['API_MAIL'], email,
         'Your blacklist entry has been removed!',
         current_app.config['BLACKLIST_REMOVED'] % fields)
