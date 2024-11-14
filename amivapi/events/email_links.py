# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Email confirmation logic.

Needed when external users want to sign up for public events or users want to
sign off via links.
"""
from bson import ObjectId
from eve.methods.delete import deleteitem_internal
from eve.methods.patch import patch_internal
from flask import Blueprint, current_app, redirect
from itsdangerous import BadSignature, URLSafeSerializer

from amivapi.events.queue import update_waiting_list
from amivapi.events.utils import get_token_secret
from amivapi.events.emails import notify_signup_accepted

email_blueprint = Blueprint('emails', __name__)


def add_confirmed_before_insert(items):
    """Add the confirmed field to a event signup before it is inserted to the
    database. We accept all registered users instantly, others need to click the
    confirmation link first"""
    for item in items:
        if item.get('user', None) is None:
            item['confirmed'] = False
        else:
            item['confirmed'] = True


@email_blueprint.route('/confirm_email/<token>')
def on_confirm_email(token):
    """Email confirmation endpoint.

    We try to confirm the specified signup and redirect to a webpage.
    """
    try:
        s = URLSafeSerializer(get_token_secret())
        signup_id = ObjectId(s.loads(token))
    except BadSignature:
        return "Unknown token"

    patch_internal('eventsignups', {'confirmed': True},
                   skip_validation=True, concurrency_check=False,
                   **{current_app.config['ID_FIELD']: signup_id})

    # Now the user may be able to get accepted, so update the events waiting
    # list
    lookup = {current_app.config['ID_FIELD']: signup_id}
    signup = current_app.data.find_one('eventsignups', None, **lookup)

    update_waiting_list(signup['event'])

    # refresh the signup to get the updated data
    signup = current_app.data.find_one('eventsignups', None, **lookup)
    if signup.get["accepted"]==False:
        # if the user is on the waitinglist he doesn't get notified automatically. 
        notify_signup_accepted(signup['event'], signup,True)

    redirect_url = current_app.config.get('EMAIL_CONFIRMED_REDIRECT')
    if redirect_url:
        return redirect(redirect_url)
    else:
        return current_app.config['CONFIRM_TEXT']


@email_blueprint.route('/delete_signup/<token>')
def on_delete_signup(token):
    """Endpoint to delete signups via email"""
    try:
        s = URLSafeSerializer(get_token_secret())
        signup_id = ObjectId(s.loads(token))
    except BadSignature:
        return "Unknown token"

    deleteitem_internal('eventsignups', concurrency_check=False,
                        **{current_app.config['ID_FIELD']: signup_id})

    redirect_url = current_app.config.get('SIGNUP_DELETED_REDIRECT')
    if redirect_url:
        return redirect(redirect_url)
    else:
        return current_app.config['SIGNUP_DELETED_TEXT']
