# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Email confirmation logic.

Needed when external users want to sign up for public events.
"""
from flask import current_app
from flask import Blueprint, request, abort, g

from eve.methods.post import post
from eve.render import send_response
from eve.methods.common import payload

from amivapi.auth.authorization import common_authorization
from amivapi import models, utils

confirmprint = Blueprint('confirm', __name__)


def send_confirmmail(resource, token, email):
    """Send mail. Not implemented.

    For the development-Version, we do not actually send emails but print
    the token. For testing, you will find the token in the database or copy it
    from the command-line
    :param resource: The resource of the current request as a string
    :param token: The token connected to the data-entry which needs
    confirmation
    :param email: address the email will be send to
    """
    print('email send with token %s to %s' % (token, email))


def confirm_actions(resource, email, items):
    """Create unique token needed for confirmation.

    This method will generate a random token and append it to items.
    For 'eventsignups', the email will be swapped to the key '_email_unreg'.
    An email will be send to the user for confirmation.
    :param resource: the ressource current as a string
    :param items: the dictionary of the data which will be inserted into the
    database
    :param email: The email the confirmation mail will be send to
    """
    token = utils.token_generator(size=20)
    send_confirmmail(resource, token, email)
    if resource == 'eventsignups':
        # email is no relation, move it to _email_unreg
        items.pop('email')
        items['_email_unreg'] = email
    items['_token'] = token


def change_status(response):
    """Change status to "accepted" for actions that need confirmation.

    This function changes the caught. response of a post. Eve returns 201
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
                            current_app.config['STATUS']: 202})
        return response[0], None, None, 202
    return response


def route_post(resource, lookup, anonymous=True):
    """Post endpoint to be able to change status.

    This method maps the request to the corresponding eve-functions or
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


documentation = {'eventsignups': {
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
        'additional fields': "Needs to provide all necessary data defined in "
        "event.additional_fields",
        'user_id': "If you are not registered, set this to -1"
    },
    'schema': 'eventsignups'
}}


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
    """Confirmation token endpoint.

    :returns: 201 if token correct
    """
    data = payload()
    return execute_confirmed_action(data.get('token'))


def execute_confirmed_action(token):
    """Do whatever needed confirmation.

    from a given token, this function will search for a stored action in
    Confirms and send it to eve's post_internal
    PATCH and PUT are not implemented yet
    :param token: the Token which was send to an email-address for confirmation
    :returns: 201 in eve-response-format, without confirmed data
    """
    db = current_app.data.driver.session
    signup = db.query(models.EventSignup).filter_by(_token=token).first()
    doc = signup
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


def signups_confirm_anonymous(items):
    """Hook to confirm external signups."""
    for doc in items:
        if doc['user_id'] == -1:
            doc['_confirmed'] = False
            confirm_actions('eventsignups', doc['email'], doc)
        else:
            doc['_confirmed'] = True


def needs_confirmation(resource, doc):
    """Check if confirmation is needed."""
    return (resource == 'eventsignups' and
            doc.get('_email_unreg') is not None)


def pre_delete_confirmation(resource, original):
    """Hook to check if confirmation is needed."""
    if needs_confirmation(resource, original):
        token_authorization(resource, original)


def pre_update_confirmation(resource, updates, original):
    """Hook to check if confirmation is needed."""
    pre_delete_confirmation(resource, original)


def pre_replace_confirmation(resource, document, original):
    """Hook to check if confirmation is needed."""
    pre_delete_confirmation(resource, original)


def token_authorization(resource, original):
    """Check confirmation token.

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
        print("Access to %s/%d granted for owner %d without token" % (
            resource, original['id'], g.logged_in_user))
        return
    if g.resource_admin:
        print("Access to %s/%d granted for admin %d without token" % (
            resource, original['id'], g.logged_in_user))
        return
    if token is None:
        # consistent with _etag
        abort(403, description="Please provide a valid token.")
    if token != original['_token']:
        # consistent with _etag
        abort(412, description="Token for external user not valid.")


# Remove fields _email_unreg and _token
def _replace(item, old_key, new_key):
    if item.get(old_key):
        item[new_key] = item.pop(old_key)


# Hooks for input
def replace_email_insert(items):
    """List of inserted items."""
    for item in items:
        _replace(item, 'email', '_email_unreg')


def replace_email_replace(item, original):
    """One item."""
    _replace(item, 'email', '_email_unreg')


def replace_email_update(updates, original):
    """One item."""
    _replace(updates, 'email', '_email_unreg')


# Hooks for output
def replace_email_fetched_item(response):
    """The response will contain exactly one item."""
    _replace(response, '_email_unreg', 'email')


def replace_email_fetched_resource(response):
    """The response will be a dict, the list of items is in '_items'."""
    for item in response['_items']:
        _replace(item, '_email_unreg', 'email')


def replace_email_replaced(item, original):
    """The response will be a dict, the list of items is in '_items'."""
    _replace(item, '_email_unreg', 'email')


def replace_email_inserted(items):
    """List of inserted items."""
    for item in items:
        _replace(item, '_email_unreg', 'email')


def replace_email_updated(updates, original):
    """One updated item."""
    _replace(updates, '_email_unreg', 'email')


# Hooks to remove '_token' from output after db access
def remove_token_fetched_item(response):
    """The response will contain exactly one item."""
    del(response['_token'])


def remove_token_fetched_resource(response):
    """Response will be a dict, the list of items is in '_items'."""
    for item in response['_items']:
        item.pop('_token', None)


def remove_token_replaced(item, original):
    """Response will be a dict, the list of items is in '_items'."""
    item.pop('_token', None)


def remove_token_inserted(items):
    """List of inserted items."""
    for item in items:
        item.pop('_token', None)