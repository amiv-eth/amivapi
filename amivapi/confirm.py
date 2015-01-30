from flask import current_app as app
from flask import Blueprint, request, abort
from amivapi.models import Confirm
from amivapi import utils
from eve.methods.post import post_internal
from eve.render import send_response

import datetime as dt
import string
import random
import json


confirmprint = Blueprint('confirm', __name__)


def id_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def send_confirmmail(ressource, token, email):
    print('email send with token %s to %s' % (token, email))


def confirm_actions(ressource, method, doc, items, email_field):
    """
    This method will save a given action for confirmation in the database
    and send a token to the email-address given.
    The action will be executed as soon as the token is POSTed to the resource
    /confirms
    :param ressource: the ressource as a string
    :param method: the method (POST, GET, DELETE) as a string
    :param doc: the dictionary of the data for the action
    :param items: a list of all data processed by the hook. This is only needed
                  to delete the doc out of this list.
    :param email_field: the key for the email-address in doc
    """

    if doc.get('_confirmed') is not True:
        doc.pop('_updated')
        doc.pop('_created')
        doc.pop('_author')
        data = json.dumps(doc, cls=utils.DateTimeEncoder)
        expiry = dt.datetime.now() + dt.timedelta(days=14)
        # TODO: check uniqueness of token?
        token = id_generator(size=20)
        thisconfirm = Confirm(
            method=method,
            ressource=ressource,
            data=data,
            expiry_date=expiry,
            token=token,
            _author=0,
        )
        db = app.data.driver.session
        db.add(thisconfirm)
        db.commit()
        send_confirmmail(ressource, token, doc.get(email_field))
        items.remove(doc)
    else:
        doc.pop('_confirmed')


def return_status(payload):
    # payload.data might get deprecated
    data = json.loads(payload.get_data())
    if payload.status_code is 201 and 'id' not in data:
        """No items actually inserted but saved in Confirm,
        Send 202 Accepted"""
        payload.status_code = 202
        data.update({'_issue': 'Please check your email and POST the token '
                    'to /confirms to process your request'})
        payload.data = data


@confirmprint.route('/confirms', methods=['POST'])
def on_post_token():
    data = utils.parse_data(request)
    return execute_confirmed_action(data.get('token'))


def execute_confirmed_action(token):
    db = app.data.driver.session
    action = db.query(Confirm).filter_by(
        token=token
    ).first()
    # TODO: check expiry_date
    if action is None:
        abort(404, description=(
            'This token could not be found. It might got expired.'
        ))
    payload = json.loads(action.data, cls=utils.DateTimeDecoder)
    payload.update({'_confirmed': True})
    response = None
    if action.method == 'POST':
        answer = post_internal(action.ressource, payload)
        response = send_response(action.ressource, answer)
    db.delete(action)
    db.commit()
    return response
