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


def sendConfirmmail(ressource, token, email):
    print('email send with token %s to %s' % (token, email))


def confirmActions(ressource, method, condition, items, email_field):
    """
    :param ressource: the ressource as a string
    :param method: the method (POST, GET, DELETE) as a string
    :param condition: a dict with 'doc-key' and 'value' for the condition

    """
    for doc in items:
        if doc.get(condition.get('doc-key')) == condition.get('value'):
            if doc.get('_confirmed') is not True:
                doc.pop('_updated')
                doc.pop('_created')
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
                )
                db = app.data.driver.session
                db.add(thisconfirm)
                db.commit()
                sendConfirmmail(ressource, token, doc.get(email_field))
                items.remove(doc)
            else:
                doc.pop('_confirmed')


def return_status(payload):
    """Send 202 Accepted"""
    payload.status_code = 202
    #payload.data might get deprecated
    message = payload.get_data()[:payload.data.find('}')]
    message += (
        ', "_issue":"Please check your email and POST the token '
        'to /confirms to process your request"}'
    )
    payload.data = message


@confirmprint.route('/confirms', methods=['POST'])
def onPostToken():
    data = utils.parse_data(request)
    return executeConfirmedAction(data.get('token'))


def executeConfirmedAction(token):
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
