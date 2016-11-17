# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Sessions endpoint."""

from os import urandom
from base64 import b64encode
from bson import ObjectId
from bson.errors import InvalidId
import datetime

from flask import abort, current_app as app
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from eve.utils import debug_error_message, config

from amivapi.cron import periodic
from amivapi.utils import admin_permissions
from .auth import AmivTokenAuth


class SessionAuth(AmivTokenAuth):
    """Simple auth for session.

    No resource write check needed since POST is public.
    """

    def has_item_write_permission(self, user_id, item):
        """Allow users to modify only their own sessions."""
        # item['user'] is Objectid, convert to str
        return user_id == str(item['user'])

    def create_user_lookup_filter(self, user_id):
        """Allow users to only see their own sessions."""
        return {'user': user_id}


sessiondomain = {
    'sessions': {
        'description': {
            'general': "A session is used to authenticate a user after he "
            "provided login data. A POST to /session will return a token you "
            "can use in an Authorization header: token <yourtoken>",
            'methods': {
                'POST': "Login and aquire a login token. Post the fields "
                "'username' and 'password', the response will contain the "
                "token. 'username' can be either nethz, mail, or user_id",
                'GET': "Check token(s)."}
        },

        'authentication': SessionAuth,
        'public_methods': ['POST'],
        'public_item_methods': [],
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'DELETE'],

        'schema': {
            'username': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False},
            'password': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False},
            'user': {'type': 'objectid',
                     'data_relation': {
                         'resource': 'users',
                         'field': '_id',
                         'embeddable': True,
                         'cascade_delete': True
                     },
                     'readonly': True},
            'token': {'type': 'string',
                      'readonly': True}
        },
    }
}


# Login Hook

def process_login(items):
    """Hook to add token on POST to /sessions.

    Attempts to first login via LDAP (if enabled), then login via database.

    Root login is possible if 'user' is 'root' (instead of nethz or mail).
    This shortcut is hardcoded.

    TODO (ALEX): make root user shortcut a setting maybe.

    If the login is successful, the fields "username" and "password" are
    removed and the fields "user" and "token" are added, which will be stored
    in the db.

    If the login is unsuccessful, abort(401)

    Args:
        items (list): List of items as passed by EVE to post hooks.
    """
    for item in items:  # TODO (Alex): Batch POST doesnt really make sense
        username = item['username']
        password = item['password']

        # LDAP
        if (config.ENABLE_LDAP and
                ldap_connector.authenticate_user(username, password)):
            # Success, sync user and get token
            updated = ldap_connector.sync_one(username)
            _prepare_token(item, updated['_id'])
            app.logger.info(
                "User '%s' was authenticated with LDAP" % username)
            return

        # Database, try to find via nethz, mail or objectid
        users = app.data.driver.db['users']
        lookup = {'$or': [{'nethz': username}, {'email': username}]}
        try:
            objectid = ObjectId(username)
            lookup['$or'].append({'_id': objectid})
        except InvalidId:
            pass  # input can't be used as ObjectId
        user = users.find_one(lookup)

        if user:
            app.logger.debug("User found in db.")
            if verify_password(user, item['password']):
                app.logger.debug("Login for user '%s' successful." % username)
                _prepare_token(item, user['_id'])
                return
            else:
                status = "Login failed: Password does not match!"
                app.logger.debug(status)
                abort(401, description=debug_error_message(status))

        # Abort if everything else fails
        status = "Login with db failed: User not found!"
        app.logger.debug(status)
        abort(401, description=debug_error_message(status))


def _prepare_token(item, user_id):
    token = b64encode(urandom(256)).decode('utf_8')

    # Make sure token is unique
    while app.data.find_one("sessions", None, token=token) is not None:
        token = b64encode(urandom(256)).decode('utf_8')

    # Remove user and password from document
    del item['username']
    del item['password']

    # Add token (str) and user_id (ObejctId)
    item['user'] = user_id
    item['token'] = token


def verify_password(user, plaintext):
    """Check password of user, rehash if necessary.

    It is possible that the password is None, e.g. if the user is authenticated
    via LDAP. In this case default to "not verified".

    Args:
        user (dict): the user in question.
        plaintext (string): password to check

    Returns:
        bool: True if password matches. False if it doesn't or if there is no
            password set and/or provided.
    """
    password_context = app.config['PASSWORD_CONTEXT']

    if (plaintext is None) or (user['password'] is None):
        return False

    is_valid = password_context.verify(plaintext, user['password'])

    if is_valid and password_context.needs_update(user['password']):
        # update password - hook will handle hashing
        update = {'password': plaintext}
        with admin_permissions():
            patch_internal("users", payload=update, _id=user['_id'])
    return is_valid


# Regular task to clean up expired sessions
@periodic(datetime.timedelta(days=1))
def delete_expired_sessions():
    """Delete expired sessions.

    Needs an app context to access current_app,
    make sure to create one if necessary.

    E.g.
    >>> with app.app_context():
    >>>     delete_expired_sessions()
    """
    deadline = datetime.datetime.utcnow() - app.config['SESSION_TIMEOUT']
    app.data.driver.db['sessions'].remove({'_updated': {'$lt': deadline}})
