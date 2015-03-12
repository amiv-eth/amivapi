from flask import current_app as app
from flask import Blueprint, request, abort, g
from eve.methods.post import post_internal, post
from eve.methods.delete import deleteitem
from eve.methods.get import get, getitem
from eve.methods.patch import patch
from eve.methods.put import put
from eve.render import send_response
from eve.methods.common import payload, get_document
from eve.utils import config, request_method
from amivapi.authorization import common_authorization

import datetime as dt
import string
import random
import json

import models
import utils


confirmprint = Blueprint('confirm', __name__)
documentation = {}


def id_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def send_confirmmail(ressource, token, email):
    """For the development-Version, we do not actually send emails but print
    the token. For testing, you will find the token in the database or copy it
    from the command-line"""
    print('email send with token %s to %s' % (token, email))


def confirm_actions(resource, method, doc):
    """
    This method will save a given action for confirmation in the database
    and send a token to the email-address given.
    The action will be executed as soon as the token is POSTed to the resource
    /confirmations

    :param ressource: the ressource as a string
    :param method: the method (POST, GET, DELETE) as a string
    :param doc: the dictionary of the data for the action
    :param items: a list of all data processed by the hook. This is only needed
                  to delete the doc out of this list.
    :param email_field: the key for the email-address in doc
    """

    # for the different resources there are different tablenames for the email
    email_field = {'_forwardaddresses': 'address',
                   '_eventsignups': 'email'}

    # if registered user has admin-rights, we need no confirmation
    if (doc.get('_confirmed', False) is not True):
        # these fields will get inserted automatcally and must not be part of
        # the payload
        doc.pop('_updated', None)
        doc.pop('_created', None)
        doc.pop('_author', None)
        data = json.dumps(doc, cls=utils.DateTimeEncoder)
        expiry = dt.datetime.now() + dt.timedelta(days=14)
        token = id_generator(size=20)
        thisconfirm = models.Confirm(
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
        doc.pop('_confirmed', None)
        return True


def change_status(response):
    """This function changes the catched response of a post. Eve returns 201
    because the data got just deleted out of the payload and the empty payload
    got handled correct, but we need to return 202 and a hint to confirm the
    email-address"""
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
    common_authorization(resource, method)
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
    :param anonymous: True if the request concerns an anonymous user (the
        logged in user may be different)
    """
    response = None
    method = request_method()
    common_authorization(resource, method)
    admin = g.resource_admin
    if method in ('GET', 'HEAD'):
        response = getitem(resource, lookup)
    elif method == 'PATCH':
        response = patch(resource, lookup)
        if anonymous and not admin:
            response = change_status(response)
    elif method == 'PUT':
        response = put(resource, lookup)
        if anonymous and not admin:
            response = change_status(response)
    elif method == 'DELETE':
        print g.logged_in_user
        db = app.data.driver.session
        resource_class = utils.get_class_for_resource(resource)
        doc = db.query(resource_class).get(lookup['_id'])
        if not doc:
            abort(404)
        print doc.__owner__
        owner = doc.__owner__ == g.logged_in_user
        print "is owner: %s" % str(owner)
        if anonymous and not admin and not owner:
            # own funcionality for confirmation, we don't use eve in this case
            # we need the email to send the token
            lookup.update(address=doc.address)
            confirm_actions(resource, method, lookup)
            response = [{}, None, None, 202]
            response[0][config.STATUS] = 202
        else:
            response = deleteitem(resource, lookup)
    elif method == 'OPTIONS':
        response = None
    else:
        abort(405)
    return send_response(resource, response)


documentation['forwardaddresses'] = {
    'general': "This resource organizes email-addresses subscribing a forward"
    " which are not relating to a user.",
    'methods': "To add an address to a forward, one must either be admin or "
    "owner of the forward. In other cases, you can POST subscriptions to "
    "public forwards. Every POST needs confirmation of the email-address.",
    'schema': '_forwardaddresses'
}


@confirmprint.route('/forwardaddresses',
                    methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def handle_forwardaddresses():
    """These are custom api-endpoints from the confirmprint Blueprint.
    We need one for the generel resource and one for the item endpoint."""

    data = request.view_args
    if request.method == 'POST':
        data = payload()
    return route_method('_forwardaddresses', data)


@confirmprint.route('/forwardaddresses/<regex("[0-9]+"):_id>',
                    methods=['GET', 'HEAD', 'DELETE', 'OPTIONS'])
def handle_forwardaddressesitem(_id):
    payload = {'_id': _id}
    return route_itemmethod('_forwardaddresses', payload)


documentation['eventsignups'] = {
    'general': "Signing up to an event is possible in two cases: Either you "
    "are a registered user ot you are not registered, but the event is "
    "public and you have an email-address.",
    'methods': {
        'GET': "You can onyl see your own signups unless you are an "
        "administrator",
        'POST': "If you are not registered, the signup becomes valid as you "
        "confirm your email-address"
    },
    'fields': {
        'extra_data': "Needs to provide all necessary data defined in "
        "event.additional_fields",
        'user_id': "If you are not registered, set this to -1"
    },
    'schema': '_eventsignups'
}


@confirmprint.route('/eventsignups',
                    methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def handle_eventsignups():
    data = request.view_args
    if request.method == 'POST':
        data = payload()
    anonymous = (data.get('user_id') == -1)
    return route_method('_eventsignups', data, anonymous)


@confirmprint.route('/eventsignups/<regex("[0-9]+"):_id>',
                    methods=['GET', 'HEAD', 'PUT', 'PATCH', 'DELETE',
                             'OPTIONS'])
def handle_eventsignupsitem(_id):
    # lookup = {config.ID_FIELD: _id}
    doc = get_document('_eventsignups', {config.ID_FIELD: _id})
    anonymous = doc.user_id == -1
    lookup = request.view_args
    return route_itemmethod('_eventsignups', lookup, anonymous)


@confirmprint.route('/confirmations', methods=['POST'])
def on_post_token():
    """This is the endpoint, where confirmation-tokens need to get posted to"""
    data = payload()  # we only allow POST -> no error with payload()
    return execute_confirmed_action(data.get('token'))


def execute_confirmed_action(token):
    """from a given token, this function will search for a stored action in
    Confirms and send it to eve's post_internal
    PATCH and PUT are not implemented yet
    """
    db = app.data.driver.session
    action = db.query(models.Confirm).filter_by(
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
        app.data.remove(action.resource,
                        {config.ID_FIELD: payload['_id']})
        response = send_response(action.resource, ({}, None, None, 200))
    else:
        abort(405)
    db.delete(action)
    db.commit()
    return response


""" Hooks to catch actions which should be confirmed """


def signups_confirm_anonymous(items):
    """
    hook to confirm external signups
    """
    for doc in items:
        if doc['user_id'] == -1:
            if not confirm_actions(
                resource='_eventsignups',
                method='POST',
                doc=doc,
            ):
                items.remove(doc)


def forwardaddresses_insert_anonymous(items):
    for doc in items:
        if not confirm_actions(
            resource='_forwardaddresses',
            method='POST',
            doc=doc,
        ):
            items.remove(doc)
