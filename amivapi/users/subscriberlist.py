# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Provide an endpoint to access the newsletter subscribers with BasicAuth."""

from flask import abort, request, current_app, Blueprint


blueprint = Blueprint('subscriber_list', __name__)


@blueprint.route('/newslettersubscribers', methods=['GET'])
def subscriberlist():
    """Return list of newsletter subscribers if authorized.

    The list has the format:

        email\tfirstname lastname
        email\tfirstname lastnamer
        ...

    The endpoint is secured by Basic Auth. Username and password need to be
    specified in the app config with the keys:

        SUBSCRIBER_LIST_USERNAME
        SUBSCRIBER_LIST_PASSWORD
    """
    if check_auth():
        collection = current_app.data.driver.db['users']
        subscribers = collection.find({'send_newsletter': True})
        return "".join('%s\t%s %s\n'
                       % (user['email'], user['firstname'], user['lastname'])
                       for user in subscribers)

    abort(401)


def check_auth():
    """Compare request basic auth with settings."""
    auth = request.authorization
    user = current_app.config['SUBSCRIBER_LIST_USERNAME']
    password = current_app.config['SUBSCRIBER_LIST_PASSWORD']
    return (request.authorization and
            (auth['username'] == user) and (auth['password'] == password))


def init_subscriber_list(app):
    """Register the subscriber list blueprint if auth is provided."""
    user = app.config['SUBSCRIBER_LIST_USERNAME']
    password = app.config['SUBSCRIBER_LIST_PASSWORD']

    if (user or password) and not (user and password):
        raise ValueError("You need to specify both username and password to "
                         "make the newsletter subscriber list available.")
    else:
        app.register_blueprint(blueprint)
