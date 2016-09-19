# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Sessions endpoint."""

from os import urandom
from base64 import b64encode
from bson import ObjectId

from flask import abort, current_app as app
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from eve.utils import debug_error_message, config

from .auth import AmivTokenAuth


class SessionAuth(AmivTokenAuth):
    """Simple auth for session."""

    def has_write_permission(self, user_id, item):
        """Allow users to modify only their own sessions."""
        return user_id == item['user_id']

    def create_user_lookup_filter(self, user_id):
        """Allow users to only see their own sessions."""
        return {'user_id': user_id}


sessiondomain = {
    'sessions': {
        'description': {
            'general': "A session is used to authenticate a user after he "
            " provided login data. To acquire a session use POST, which will "
            " give you a token to use as the user field of HTTP basic auth "
            " header with an empty password. POST requires user and password "
            " fields.",
            'methods': {
                'POST': "Login and aquire a login token. Post the fields "
                "'user' and 'password', the response will contain the token."}
        },

        'authentication': SessionAuth,
        'public_methods': ['POST'],
        'public_item_methods': [],
        'resource_methods': ['GET', 'POST', 'DELETE'],
        'item_methods': ['GET', 'DELETE'],

        'schema': {
            'user': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False},
            'password': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False},
            'user_id': {'type': 'objectid',
                        'readonly': True},
            'token': {'type': 'string',
                      'readonly': True}
        },
    }
}


# Login Hook

def process_login(items):
    """Hook to add token on POST to /sessions.

    Attempts login via LDAP if enabled first, then login via database.

    Root login is possible if 'user' is 'root' (instead of nethz or mail).
    This shortcut is hardcoded.

    TODO (ALEX): make root user shortcut a setting maybe.

    If the login is successful, the fields "user" and "password" are removed
    and the fields "user_id" and "token" are added, which will be stored in the
    db.

    If the login is unsuccessful, abort(401)

    Args:
        items (list): List of items as passed by EVE to post hooks.
    """
    for item in items:  # TODO (Alex): Batch POST doesnt really make sense
        # PHASE 1: LDAP
        # If LDAP is enabled, try to authenticate the user
        # If this is successful, create/update user data
        # Do not send any response. Although this leads to some db requests
        # later, this helps to clearly seperate LDAP and login.
        if config.ENABLE_LDAP:
            app.logger.debug("LDAP authentication enabled. Trying "
                             "to authenticate '%s'..." % item['user'])

            ldap_data = app.ldap_connector.check_user(item['user'],
                                                      item['password'])

            if ldap_data is not None:  # ldap success
                app.logger.debug("LDAP authentication successful. "
                                 "Checking database...")

                # Query db for user by nethz field
                user = app.data.find_one('users', None, nethz=item['user'])

                # Create or update user
                if user is not None:
                    app.logger.debug("User already in database. Updating...")
                    # Membership status will only be upgraded automatically
                    # If current Membership is not none ignore the ldap result
                    if user['membership'] is not None:
                        del ldap_data['membership']

                    # First element of response tuple is data
                    user = patch_internal('users',
                                          ldap_data,
                                          skip_validation=True,
                                          id=user['id'])[0]
                    app.logger.debug("User '%s' was updated." % item['user'])
                else:
                    app.logger.debug("User not in database. Creating...")

                    # Set Mail now
                    ldap_data['email'] = "%s@ethz.ch" % ldap_data['nethz']

                    # First element of response tuple is data
                    user = post_internal('users',
                                         ldap_data,
                                         skip_validation=True)[0]

                    app.logger.debug("User '%s' was created." % item['user'])

                # Success, get token
                _prepare_token(item, user['id'])
                return
            else:
                app.logger.debug("LDAP authentication failed.")
        else:
            app.logger.debug("LDAP authentication deactivated.")

        # PHASE 2: database
        # Query user by nethz or email now

        # Query user by nethz or email. Since they cannot be the same and
        # both have to be unique we ca safely use find_one()
        users = app.data.driver.db['users']

        lookup = {'$or': [{'nethz': item['user']},
                          {'email': item['user']}]}
        try:
            objectid = ObjectId(item['user'])
            lookup['$or'].append({'_id': objectid})
        except:
            # input can't be used as ObjectId -> no need to look for it
            pass

        user = users.find_one(lookup)

        if user is not None:
            app.logger.debug("User found in db.")
            if verify_password(user, item['password']):
                # Success
                app.logger.debug(
                    "Login for user '%s' successful." % item['user'])
                _prepare_token(item, user['_id'])
                return
            else:
                status = "Login failed: Password does not match!"
                app.logger.debug(status)
                abort(401, description=debug_error_message(status))

        # root user shortcut: If user is root additionally try login as root.
        # Unless someone as nethz 'root' and the exact root password there
        # will be no collision this way
        if item['user'] == 'root':
            app.logger.debug("Trying to log in as root.")
            root = users.find_one({'_id': app.config['ROOT_ID']})
            if root is not None and verify_password(root, item['password']):
                app.logger.debug("Login as root successful.")
                _prepare_token(item, app.config['ROOT_ID'])
                return

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
    del item['user']
    del item['password']

    # Add token (str) and user_id (ObejctId)
    item['user_id'] = user_id
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
        patch_internal("users", payload=update, _id=user['_id'])
    return is_valid
