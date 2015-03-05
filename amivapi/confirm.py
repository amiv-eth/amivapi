from flask import current_app as app
from flask import Blueprint, request, abort
from amivapi.models import Confirm
from amivapi import utils
from eve.methods.post import post_internal, post
from eve.methods.delete import deleteitem
from eve.methods.get import get, getitem
from eve.methods.patch import patch
from eve.methods.put import put
from eve.render import send_response
from eve.methods.common import payload, get_document
from eve.utils import request_method, config

import datetime as dt
import string
import random
import json


confirmprint = Blueprint('confirm', __name__)


def id_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def send_confirmmail(ressource, token, email):
    print('email send with token %s to %s' % (token, email))


def confirm_actions(resource, method, doc):
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

    email_field = {'_forwardaddresses': 'address',
                   '_eventsignups': 'email'}
    if doc.get('_confirmed', False) is not True:
        doc.pop('_updated', None)
        doc.pop('_created', None)
        doc.pop('_author', None)
        data = json.dumps(doc, cls=utils.DateTimeEncoder)
        expiry = dt.datetime.now() + dt.timedelta(days=14)
        # TODO: check uniqueness of token?
        token = id_generator(size=20)
        thisconfirm = Confirm(
            method=method,
            resource=resource,
            data=data,
            expiry_date=expiry,
            token=token,
            _author=0
        )
        db = app.data.driver.session
        db.add(thisconfirm)
        db.commit()
        send_confirmmail(resource, token, doc.get(email_field.get(resource)))
        return False
    else:
        doc.pop('_confirmed')
        return True


def change_status(response):
    """This function changes the catched response of a post. Eve returns 201
    because the data got just deleted out of the payload, but we need to return
    202 and a hint to confirm the data"""
    if response[3] in [201, 200] and 'id' not in response:
        """No items actually inserted but saved in Confirm,
        Send 202 Accepted"""
        response[0].update({'_issue': 'Please check your email and POST the '
                           'token to /confirms to process your request',
                            config.STATUS: 202})
        return response[0], None, None, 202
    return response


def route_method(resource, lookup, anonymous=True):
    """This method mappes the request to the corresponding eve-functions or
    implements own functions.
    Similar to eve.endpoint
    :param resource: the resource where the request comes from
    :param lookup: the lookup-dictionary like in the hooks
    :param anonymous: True if the request needs confirmation via email
    """
    response = None
    method = request_method()
    if method in ('GET', 'HEAD'):
        response = get(resource, lookup)
    elif method == 'POST':
        response = post(resource)
        if anonymous:
            response = change_status(response)
    elif method == 'OPTIONS':
        response = None
    else:
        abort(405)
    return send_response(resource, response)


def route_itemmethod(resource, lookup, anonymous=True):
    """This method mappes the request to the corresponding eve-functions or
    implements own functions.
    Similar to eve.endpoint
    :param resource: the resource where the request comes from
    :param lookup: the lookup-dictionary like in the hooks
    :param anonymous: True if the request needs confirmation via email
    """
    response = None
    method = request_method()
    if method in ('GET', 'HEAD'):
        response = getitem(resource, lookup)
    elif method == 'PATCH':
        response = patch(resource, lookup)
        if anonymous:
            response = change_status(response)
    elif method == 'PUT':
        response = put(resource, lookup)
        if anonymous:
            response = change_status(response)
    elif method == 'DELETE':
        if anonymous:
            """own funcionality for confirmation, we don't use eve in this
            case"""
            doc = get_document(resource, lookup)
            if not doc:
                abort(404)
            # we need the email to send the token
            lookup.update(address=doc.get('address'))
            confirm_actions(resource, method, lookup)
            response = [{}, None, None, 202]
            response[0][config.STATUS] = 202
        else:
            deleteitem(resource, lookup)
    elif method == 'OPTIONS':
        response = None
    else:
        abort(405)
    return send_response(resource, response)


@confirmprint.route('/forwardaddresses',
                    methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def handle_forwardaddresses():
    data = request.view_args
    if request.method == 'POST':
        data = payload()
    return route_method('_forwardaddresses', data)


@confirmprint.route('/forwardaddresses/<_id>',
                    methods=['GET', 'HEAD', 'DELETE', 'OPTIONS'])
def handle_forwardaddressesitem(_id):
    payload = {'_id': _id}
    return route_itemmethod('_forwardaddresses', payload)


@confirmprint.route('/eventsignups',
                    methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def handle_eventsignups():
    data = request.view_args
    if request.method == 'POST':
        data = payload()
    anonymous = (data.get('user_id') == -1)
    return route_method('_eventsignups', data, anonymous)


@confirmprint.route('/eventsignups/<_id>',
                    methods=['GET', 'HEAD', 'PUT', 'PATCH', 'DELETE',
                             'OPTIONS'])
def handle_eventsignupsitem(_id):
    # lookup = {config.ID_FIELD: _id}
    lookup = request.view_args
    doc = get_document('_eventsignups', {config.ID_FIELD: _id})
    return route_itemmethod('_eventsignups', lookup, doc.user_id == -1)


@confirmprint.route('/confirmations', methods=['POST'])
def on_post_token():
    """This is the endpoint, where confirmation-tokens need to get posted to"""
    data = payload()  # we only allow POST
    return execute_confirmed_action(data.get('token'))


def execute_confirmed_action(token):
    """from a given token, this function will search for a stored action in
    Confirms and send it to eve's post_internal
    PATCH and PUT are not implemented yet
    """
    db = app.data.driver.session
    action = db.query(Confirm).filter_by(
        token=token
    ).first()
    if action is None:
        abort(404, description=(
            'This token could not be found. It might got expired.'
        ))
    payload = json.loads(action.data, cls=utils.DateTimeDecoder)
    payload.update({'_confirmed': True})
    response = None
    if action.method == 'POST':
        answer = post_internal(action.resource, payload)
        response = send_response(action.resource, answer)
    elif action.method == 'DELETE':
        app.data.remove(action.resource, {config.ID_FIELD: payload['_id']})
        response = send_response(action.resource, ({}, None, None, 200))
    else:
        abort(405)
    db.delete(action)
    db.commit()
    return response
