# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Logic to send emails on blacklist changes (deleted items don't triggger an
email because this should only happen in the case that an error occurred,
in which case the person is informed personally)"""

from flask import current_app

from amivapi.utils import mail
from datetime import datetime


def notify_new_blacklist(items):
    """Send an email to a user who has a new blacklist entry"""

    if current_app.config.get('SERVER_NAME') is None:
        current_app.logger.warning("SERVER_NAME is not set. E-Mail links "
                                   "will not work!")

    for item in items:
        id_field = current_app.config['ID_FIELD']

        lookup = {id_field: item['user']}
        user = current_app.data.find_one('users', None, **lookup)
        # name = user['firstname']
        email = user['email']

        fields = {
            'reason': item['reason'],
        }

        if item['price']:
            fields['price'] = item['price']/100
            mail(current_app.config['API_MAIL'], email,
                 '[AMIV] Blacklisted!',
                 current_app.config['BLACKLIST_ADDED_EMAIL_W_PRICE'] % fields)
        else:
            mail(current_app.config['API_MAIL'], email,
                 '[AMIV] Blacklisted!',
                 current_app.config['BLACKLIST_ADDED_EMAIL_WO_PRICE'] % fields)


def notify_patch_blacklist(new, old):
    """Send an email to a user if one of his entries was updated"""

    if current_app.config.get('SERVER_NAME') is None:
        current_app.logger.warning("SERVER_NAME is not set. E-Mail links "
                                   "will not work!")

    if ((not old['end_time']) and
            'end_time' in new and new['end_time'] <= datetime.utcnow()):
        id_field = current_app.config['ID_FIELD']

        lookup = {id_field: new['user']}
        user = current_app.data.find_one('users', None, **lookup)
        # name = user['firstname']
        email = user['email']

        fields = {
            'reason': new['reason'],
        }

        mail(current_app.config['API_MAIL'], email,
             '[AMIV] Blacklist!',
             current_app.config['BLACKLIST_REMOVED'] % fields)
