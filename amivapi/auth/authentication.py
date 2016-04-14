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
from flask import abort, g

from eve.auth import TokenAuth
from eve.utils import debug_error_message, config

from sqlalchemy import exists
from sqlalchemy.orm.exc import NoResultFound

from amivapi import models
from amivapi.ldap import ldap_connector


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
            sess = dbsession.query(Session).filter(
                Session.token == token).one()
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


def _prepare_token(item, user_id):
    # Everything is alright, create token for user
    token = b64encode(urandom(256)).decode('utf_8')

    # Make sure token is unique
    while app.data.driver.session.query(Session).filter_by(
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
        user = item['user']
        password = item['password']
        # LDAP
        # If LDAP is enabled, try to authenticate the user
        # If this is successful, create/update user data and return token
        if (config.ENABLE_LDAP and
                ldap_connector.authenticate_user(user, password)):
            # Success, sync user and get token
            updated = ldap_connector.sync_one(user)
            _prepare_token(item, updated['id'])
            app.logger.info(
                "User '%s' was authenticated with LDAP" % user)
            return

        # Database
        # Query user by nethz or email now

        # Complicated query, does the following: if user specified by nethz
        # exists, take result. if not check by email
        if (app.data.driver.session.query(exists().where(
                models.User.nethz == user)).scalar()):
            user_data = app.data.driver.session.query(models.User).filter_by(
                nethz=user).one()
        elif (app.data.driver.session.query(exists().where(
                models.User.email == user)).scalar()):
            user_data = app.data.driver.session.query(models.User).filter_by(
                email=user).one()
        elif user == 'root':
            app.logger.debug("Using root user.")
            user_data = app.data.driver.session.query(models.User).filter_by(
                id=0).one()  # Using one() because root has to exists
        else:
            user_data = None  # Neither found by nethz nor email

        if user_data:
            app.logger.debug("User found in db.")
            if user_data.verify_password(password):
                app.logger.debug("Login successful.")
                # Success
                _prepare_token(item, user_data.id)
                app.logger.info(
                    "User '%s' was authenticated with the db." % user)
                return
            else:
                status = "Login failed: Password does not match!"
                app.logger.debug(status)
                abort(401, description=debug_error_message(status))

        # PHASE 3: Abort if everything else fails
        # LDAP is unsuccessful (deactivated/wrong credentials) + user not found
        status = "User '%s' could not be authenticated." % user
        app.logger.info(status)
        abort(401, description=debug_error_message(status))


# Hooks to add _author field to all database inserts

def set_author_on_insert(resource, items):
    """Hook to set the _author field for all new objects."""
    _author = getattr(g, 'logged_in_user', -1)
    for i in items:
        i['_author'] = _author


def set_author_on_replace(resource, item, original):
    """Hook to set the _author field for all replaced objects."""
    set_author_on_insert(resource, [item])
