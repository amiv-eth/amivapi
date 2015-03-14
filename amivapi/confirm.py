from flask import current_app as app
from flask import Blueprint, request, abort, g
from eve.methods.post import post
from eve.render import send_response
from eve.methods.common import payload
from eve.utils import config, debug_error_message
from amivapi.authorization import common_authorization
from amivapi import models

import string
import random
import utils

confirmprint = Blueprint('confirm', __name__)
documentation = {}


def token_generator(size=6, chars=string.ascii_letters + string.digits):
    """generates a random string of elements of chars
    :param size: length of the token
    :param chars: list of possible chars
    :returns: a random token
    """
    return ''.join(random.choice(chars) for _ in range(size))


def send_confirmmail(resource, token, email):
    """For the development-Version, we do not actually send emails but print
    the token. For testing, you will find the token in the database or copy it
    from the command-line
    :param resource: The resource of the current request as a string
    :param token: The token connected to the data-entry which needs
    confirmation
    :param email: address the email will be send to
    """
    print('email send with token %s to %s' % (token, email))


def confirm_actions(resource, email, items):
    """
    This method will generate a random token and append it to items.
    For 'eventsignups', the email will be swapped to the key '_email_unreg'.
    An email will be send to the user for confirmation.
    :param resource: the ressource current as a string
    :param items: the dictionary of the data which will be inserted into the
    database
    :param email: The email the confirmation mail will be send to
    """
    token = token_generator(size=20)
    send_confirmmail(resource, token, email)
    if resource == 'eventsignups':
        # email is no relation, move it to _email_unreg
        items.pop('email')
        items['_email_unreg'] = email
    items['_token'] = token


def change_status(response):
    """This function changes the catched response of a post. Eve returns 201
    because the data got just deleted out of the payload and the empty payload
    got handled correct, but we need to return 202 and a hint to confirm the
    email-address
    :param response: the response from eve, a list of 4 items
    :returns: new response with changed status-code
    """
    if response[3] in [201, 200] and 'id' not in response:
        """No items actually inserted but saved in Confirm,
        Send 202 Accepted"""
        response[0].update({'_issue': 'Please check your email and POST the '
                           'token to /confirms to process your request',
                            config.STATUS: 202})
        return response[0], None, None, 202
    return response


def route_post(resource, lookup, anonymous=True):
    """This method mappes the request to the corresponding eve-functions or
    implements own functions.
    Similar to eve.endpoint
    :param resource: the resource where the request comes from
    :param lookup: the lookup-dictionary like in the hooks
    :param anonymous: True if the request needs confirmation via email
    :returns: the response from eve, with correct status code
    """
    response = None
    common_authorization(resource, 'POST')
    response = post(resource)
    if anonymous:
        response = change_status(response)
    return send_response(resource, response)


documentation['forwardaddresses'] = {
    'general': "This resource organizes email-addresses subscribing a forward"
    " which are not relating to a user.",
    'methods': "To add an address to a forward, one must either be admin or "
    "owner of the forward. In other cases, you can POST subscriptions to "
    "public forwards. Every POST needs confirmation of the email-address.",
    'schema': 'forwardaddresses'
}


@confirmprint.route('/forwardaddresses', methods=['POST'])
def handle_forwardaddresses():
    """These are custom api-endpoints from the confirmprint Blueprint.
    We don't want eve to handle POST to /forwardaddresses because we need to
    change the status of the response
    :returns: eve-response with (if POST was correct) changed status-code
    """
    data = payload()  # we only allow POST -> no error with payload()
    return route_post('forwardaddresses', data)


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
    'schema': 'eventsignups'
}


@confirmprint.route('/eventsignups', methods=['POST'])
def handle_eventsignups():
    """These are custom api-endpoints from the confirmprint Blueprint.
    We don't want eve to handle POST to /eventsignups because we need to
    change the status of the response
    :returns: eve-response with (if POST was correct) changed status-code
    """
    data = payload()  # we only allow POST -> no error with payload()
    anonymous = (data.get('user_id') == -1)
    return route_post('eventsignups', data, anonymous)


@confirmprint.route('/confirmations', methods=['POST'])
def on_post_token():
    """This is the endpoint, where confirmation-tokens need to get posted to.
    :returns: 201 if token correct
    """
    data = payload()
    return execute_confirmed_action(data.get('token'))


def execute_confirmed_action(token):
    """from a given token, this function will search for a stored action in
    Confirms and send it to eve's post_internal
    PATCH and PUT are not implemented yet
    :param token: the Token which was send to an email-address for confirmation
    :returns: 201 in eve-response-format, without confirmed data
    """
    db = app.data.driver.session
    signup = db.query(models.EventSignup).filter_by(_token=token).first()
    forward = db.query(models.ForwardAddress).filter_by(_token=token).first()
    doc = signup
    if doc is None:
        doc = forward
    if doc is None:
        abort(404, description=(
            'This token could not be found.'
        ))
    resource = doc.__tablename__
    # response = patch_internal(resource, {'_confirmed': True}, False,
    #                        False, _id=doc._id)
    doc._confirmed = True
    db.flush()
    response = [{}, None, None, 201]
    # app.data.update(resource, doc._id, {'_confirmed': True})
    return send_response(resource, response)


""" Hooks to catch actions which should be confirmed """


def signups_confirm_anonymous(items):
    """
    hook to confirm external signups
    """
    for doc in items:
        if doc['user_id'] == -1:
            doc['_confirmed'] = False
            confirm_actions('eventsignups', doc['email'], doc)
        else:
            doc['_confirmed'] = True


def forwardaddresses_insert_anonymous(items):
    for doc in items:
        doc['_confirmed'] = False
        confirm_actions('forwardaddresses', doc['email'], doc)


def needs_confirmation(resource, doc):
    return (resource == 'eventsignups'
            and doc.get('_email_unreg') is not None) \
        or (resource == 'forwardaddresses')


def pre_delete_confirmation(resource, original):
    if needs_confirmation(resource, original):
        token_authorization(resource, original)


def pre_update_confirmation(resource, updates, original):
    pre_delete_confirmation(resource, original)


def pre_replace_confirmation(resource, document, original):
    pre_delete_confirmation(resource, original)


def post_deleted_confirmation(resource, item):
    if needs_confirmation(resource, item):
        return_correct_email(item)


def post_updated_confirmation(resource, updates, original):
    if needs_confirmation(resource, original):
        return_correct_email(original)


def post_fetched_confirmation(resource, response):
    post_deleted_confirmation(resource, response)


def post_inserted_confirmation(resource, items):
    for item in items:
        post_deleted_confirmation(resource, item)


def post_replaced_confirmation(resource, item, original):
    post_deleted_confirmation(resource, item)


def token_authorization(resource, original):
    """
    checks if a request to an item-endpoint is authorized by the correct Token
    in the header
    Will abort if Token is incorrect.
    :param resourse: the resource of the item as a string
    :param original: The original data of the item which is requested
    """
    token = request.headers.get('Token')
    model = utils.get_class_for_resource(models, resource)
    is_owner = g.logged_in_user in utils.get_owner(model, original['id'])
    if is_owner:
        print "Access to %s/%d granted for owner %d" % (resource,
                                                        original['id'],
                                                        g.logged_in_user)
        return
    if token is None and not g.resource_admin:
        abort(412, description=debug_error_message(
            "Please provide a valid token."
        ))
    if token != original['_token']:
        print("jop")
        abort(401, description="Token for external user not valid.")


def return_correct_email(response):
    if response.get('_email_unreg') is not None:
        response['email'] = response['_email_unreg']
        response.pop('_email_unreg')
