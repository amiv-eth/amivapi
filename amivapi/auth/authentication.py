# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
This file provides token based authentication (identification of users).

A user can POST the /sessions resource to obtain a token.

When a user sends his token with a request the g.logged_in_user global variable
will be set.
If an apikey is sent instead of a token, then g.apikey will be set to that key
and g.logged_in_user is set to -1
"""


from os import urandom
from base64 import b64encode
from datetime import datetime

from flask import current_app as app
from flask import Blueprint, abort, g

from eve.auth import TokenAuth
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from eve.utils import debug_error_message, config

from sqlalchemy import exists
from sqlalchemy.orm.exc import NoResultFound

from amivapi import models


class TokenAuth(TokenAuth):
    """Custom TokenAuth.

    We could have used eve's allowed_roles parameter, but that does not
    support roles on endpoint level, but only on resource level
    """

    def check_auth(self, token, allowed_roles, resource, method):
        """The authentication function called by eve.

        It will parse the send token and determine if it is from a valid user
        or a known apikey.

        You should not call this function directly. Use the functions in
        authorization.py instead(have a look at common_authorization()).

        :global g.logged_in_user: This is set to the user id of the
                                  authentificated user or to -1 if an apikey
                                  was sent
        :global g.apikey: If an apikey was sent it will be saved here. For a
                          normal user this will not be set

        :param token: The token or apikey sent by the user
        :param allowed_roles: unused, passed by eve
        :param resource: name of the requested resource, used for logging
        :param method: name of the requested resource, used for logging

        :returns: True if token or apikey was valid, aborts with 401 if not
        """
        # Handle apikeys
        if token in config.APIKEYS:
            g.logged_in_user = -1
            g.apikey = token
            return True

        dbsession = app.data.driver.session

        try:
            sess = dbsession.query(models.Session).filter(
                models.Session.token == token).one()
        except NoResultFound:
            error = ("Access denied for %s %s: unknown token %s"
                     % (method, resource, token))
            app.logger.debug(error)
            abort(401, description=debug_error_message(error))

        # Update last access time
        sess._updated = datetime.utcnow()
        dbsession.commit()

        g.logged_in_user = sess.user_id
        return True


authentication = Blueprint('authentication', __name__)


def _prepare_token(item, user_id):
    # Everything is alright, create token for user
    token = b64encode(urandom(256)).decode('utf_8')

    # Make sure token is unique
    while app.data.driver.session.query(models.Session).filter_by(
            token=token).count() != 0:
        token = b64encode(urandom(256)).decode('utf_8')

    # Remove user and password from document
    del item['user']
    del item['password']

    # Add token and user_id
    item['user_id'] = user_id
    item['token'] = token


# Hook

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
                has_user_nethz = app.data.driver.session.query(exists().where(
                    models.User.nethz == item['user']
                )).scalar()

                # Create or update user
                if has_user_nethz:
                    app.logger.debug("User already in database. Updating...")
                    # Get user
                    user = app.data.find_one('users', None, nethz=item['user'])

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

        # Complicated query, does the following: if user specified by nethz
        # exists, take result. if not check by email
        if (app.data.driver.session.query(exists().where(
                models.User.nethz == item['user'])).scalar()):
            user = app.data.driver.session.query(models.User).filter_by(
                nethz=item['user']).one()
        elif (app.data.driver.session.query(exists().where(
                models.User.email == item['user'])).scalar()):
            user = app.data.driver.session.query(models.User).filter_by(
                email=item['user']).one()
        elif item['user'] == 'root':
            app.logger.debug("Using root user.")
            user = app.data.driver.session.query(models.User).filter_by(
                id=0).one()  # Using one() because root has to exists
        else:
            user = None  # Neither found by nethz nor email

        if user:
            app.logger.debug("User found in db.")
            if user.verify_password(item['password']):
                app.logger.debug("Login successful.")
                # Success
                _prepare_token(item, user.id)
                return
            else:
                status = "Login failed: Password does not match!"
                app.logger.debug(status)
                abort(401, description=debug_error_message(status))

        # PHASE 3: Abort if everything else fails
        # LDAP is unsuccessful (deactivated/wrong credentials) + user not found
        status = "Login with db failed: User not found!"
        app.logger.debug(status)
        abort(401, description=debug_error_message(status))


#
#
# Hooks to add _author field to all database inserts
#
#


def set_author_on_insert(resource, items):
    """Hook to set the _author field for all new objects."""
    _author = getattr(g, 'logged_in_user', -1)
    for i in items:
        i['_author'] = _author


def set_author_on_replace(resource, item, original):
    """Hook to set the _author field for all replaced objects."""
    set_author_on_insert(resource, [item])
