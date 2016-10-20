# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Email confirmation logic.

Needed when external users want to sign up for public events.
"""

from itsdangerous import Signer, BadSignature
from bson import ObjectId

from flask import current_app, Blueprint, redirect, url_for

from eve.methods.patch import patch_internal

from amivapi.utils import mail

confirmprint = Blueprint('confirm', __name__)


def send_confirmmail_to_unregistered_users(item):
    """Send a confirmation email for external signups(email only)

    Args:
        item: The item, which was just inserted into the database
    """
    if 'user' not in item:
        event = current_app.data.find_one(
            'events', None,
            **{current_app.config['ID_FIELD']: item['event']})

        if 'title_en' in event:
            title = event['title_en']
        else:
            title = event['title_de']

        token = Signer(current_app.config['TOKEN_SECRET']).sign(
            str(item['_id']))

        fields = {
            'link': url_for('confirm.on_confirm_email', token=token,
                            _external=True),
            'title': title
        }
        email_content = current_app.config['CONFIRM_EMAIL_TEXT'] % fields

        mail(current_app.config['API_MAIL'],  # from
             [item['email']],  # receivers list
             'Registration for AMIV event %s' % title,
             email_content)


def send_confirmmail_to_unregistered_users_bulk(items):
    for item in items:
        send_confirmmail_to_unregistered_users(item)


def add_confirmed_before_insert(item):
    """Add the confirmed field to a event signup before it is inserted to the
    database. We accept all registered users instantly, others need to click the
    confirmation link first"""
    if item.get('user', None) is None:
        item['confirmed'] = False
    else:
        item['confirmed'] = True


def add_confirmed_before_insert_bulk(items):
    for item in items:
        add_confirmed_before_insert(item)


@confirmprint.route('/confirm_email/<token>')
def on_confirm_email(token):
    """Email confirmation endpoint.

    We try to confirm the specified signup and redirect to a webpage.
    """
    try:
        s = Signer(current_app.config['TOKEN_SECRET'])
        signup_id = ObjectId(s.unsign(token))
    except BadSignature:
        return "Unknown token"

    patch_internal('eventsignups', {'confirmed': True},
                   skip_validation=True, concurrency_check=False,
                   **{current_app.config['ID_FIELD']: signup_id})

    redirect_url = current_app.config.get('EMAIL_CONFIRMED_REDIRECT')
    if redirect_url:
        return redirect(redirect_url)
    else:
        return current_app.config['CONFIRM_TEXT']
