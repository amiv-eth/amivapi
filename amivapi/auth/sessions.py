# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Sessions endpoint."""

import datetime

from bson import ObjectId
from bson.errors import InvalidId
from eve.methods.patch import patch_internal
from eve.utils import debug_error_message
from flask import abort, current_app as app

from amivapi import ldap
from amivapi.auth import AmivTokenAuth
from amivapi.cron import periodic
from amivapi.utils import admin_permissions, get_id

# Change when we drop python3.5 support
try:
    from secrets import token_urlsafe
except ImportError:
    from amivapi.utils import token_urlsafe


class SessionAuth(AmivTokenAuth):
    """Simple auth for session.

    No resource write check needed since POST is public.
    """

    def has_item_write_permission(self, user_id, item):
        """Allow users to modify only their own sessions."""
        # item['user'] is Objectid, convert to str
        return user_id == str(get_id(item['user']))

    def create_user_lookup_filter(self, user_id):
        """Allow users to only see their own sessions."""
        return {'user': user_id}


DESCRIPTION = (r"""
A session is used to authenticate a user. A session is uniquely identified
by a *token*, which can be sent in the HTTP `Authorization` header.

The `/sessions` resource is a low-level interface to manage a users sessions.

For web-based applications, a high-level OAuth2 interface exists as well which
should be used whenever possible.

See [here](http://localhost:5000/docs#section/Authentication-and-Authorization)
for more information on which way to aquire a token is appropriate for you and
how to send it back to the API.

<br />

## LDAP Login

The API can act as a proxy to the ETH LDAP. If the n.ethz shortname and
password are sent in a `POST` request, the API will forward them to the ETH
LDAP and a session will be created if the LDAP login was successful.

> A successful LDAP login will also synchronize the user in the API with the
> ETH LDAP.

<br />

## API Login

If the user has set a password with the API, login is also possible using this
password instead of loging in via LDAP.

In this case, any field that uniquely identifies a user can be sent as
`username`, i.e. `nethz`, `email` or `_id`.

> The API will first attempt to log in a user via LDAP. Only if this fails,
> it will check the API password.

<br />

## Retrieving User Data on Login

To retrieve user information automatically on a succesful login without a
separate request, you can use embedding:

```
POST /sessions?embedded={"users":true}
```

In the response to your request, the user `_id` will now be replaced with the
user data.
""")


sessiondomain = {
    'sessions': {
        'description': DESCRIPTION,

        'authentication': SessionAuth,
        'public_methods': ['POST'],
        'public_item_methods': [],
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'DELETE'],

        # Allow GET requests with token, i.e. GET /sessions/<token>
        'additional_lookup': {'field': 'token', 'url': 'string'},

        'schema': {
            'username': {
                'description': '`_id`, `nethz` or `email` of a user.',
                'example': 'pablop',

                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'writeonly': True,

            },
            'password': {
                'description': 'LDAP or API password of the user.',
                'example': 'Hunter2',

                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'writeonly': True,
            },
            'user': {
                'description': 'The user to whom the session belongs.',
                'example': '438b9b7e86e7999a6acd9686',

                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'field': '_id',
                    'embeddable': True,
                    'cascade_delete': True
                },
                'readonly': True,

            },
            'token': {
                'description': 'The token uniquely identifying the session.',
                'example': 'fMtwSnJr6VRxKvXpBat1pt3TLpY8kefI4czNa1xHXps',

                'type': 'string',
                'readonly': True,
            }
        },
    }
}


# Login Hook

def process_login(items):
    """Hook to add token on POST to /sessions.

    Attempts to first login via LDAP (if enabled), then login via database.

    If the login is successful, the fields "username" and "password" are
    removed and the fields "user" and "token" are added, which will be stored
    in the db.

    If the login is unsuccessful, abort(401)

    Args:
        items (list): List of items as passed by EVE to post hooks.
    """
    for item in items:
        username = item['username']
        password = item['password']

        # LDAP
        if (app.config.get('ldap_connector') and
                ldap.authenticate_user(username, password)):
            # Success, sync user and get token
            updated = ldap.sync_one(username)
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
    token = token_urlsafe()

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
