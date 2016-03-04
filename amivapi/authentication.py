# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
This file provides token based authentication (identification of users). A
user can POST the /sessions resource to obtain a token.

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

from eve.methods.common import payload
from eve.auth import TokenAuth
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from eve.render import send_response
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


def _token_response(user_id):
    # Everything is alright, create token for user
    token = b64encode(urandom(256)).decode('utf_8')

    # Make sure token is unique
    while app.data.driver.session.query(models.Session).filter_by(
            token=token).count() != 0:
        token = b64encode(urandom(256)).decode('utf_8')

    response = post_internal(
        'sessions',
        {
            'user_id': user_id,
            'token': token
        }
    )

    return response


@authentication.route('/sessions', methods=['POST'])
def process_login():
    """Custom endpoint for POST to /sessions.

    A POST to /sessions exspects nethz and password. If they are correct a
    token is created and used to register a session in the database, which is
    sent back to the user.

    Instead of nethz email is also accepted.

    First of all we will try to authenticate the user with LDAP (if enabled).
    If this succeeds we update or create (if not yet in db) the user data

    If LDAP auth fails and the user is in the db, we will compare the received
    pw with the pw in the db.

    :returns: Flask.Response object
    """
    p_data = payload()

    schema = {
        'user': {
            'type': 'string',
            'required': True,
            'nullable': False,
            'empty': False,
        },
        'password': {
            'type': 'string',
            'required': True,
            'nullable': False
        }
    }

    # Create new validator for this schema
    v = app.validator(schema)

    # And use it
    if not v.validate(p_data):
        abort(422, description=str(v.errors))

    # PHASE 1: LDAP
    # If LDAP is enabled, try to authenticate the user
    # If this is successful, create/update user data
    # Do not send any response. Although this leads to some db requests
    # later, this helps to clearly seperate LDAP and login.
    if config.ENABLE_LDAP:
        app.logger.debug("LDAP authentication enabled. Trying to authenticate "
                         "'%s'..." % p_data['user'])

        ldap_data = app.ldap_connector.check_user(p_data['user'],
                                                  p_data['password'])

        if ldap_data is not None:  # ldap success
            app.logger.debug("LDAP authentication successful. "
                             "Updating database...")
            # Query db for user by nethz field
            has_user_nethz = app.data.driver.session.query(exists().where(
                models.User.nethz == p_data['user']
            )).scalar()

            # Create or update user
            if has_user_nethz:
                app.logger.debug("User already in database. Updating...")
                # Get user
                user = app.data.find_one('users', None, nethz=p_data['user'])

                # Membership status will only be upgraded automatically
                # If current Membership is not none ignore the ldap result
                if user['membership'] is not None:
                    ldap_data.pop('membership')

                # First element of respoinse is data
                patch_internal('users',
                               ldap_data,
                               skip_validation=True,
                               id=user['id'])
                app.logger.debug("User '%s' was updated." % p_data['user'])
            else:
                app.logger.debug("User not in database. Creating...")

                # Set Mail now
                ldap_data['email'] = "%s@ethz.ch" % ldap_data['nethz']

                post_internal('users',
                              ldap_data,
                              skip_validation=True)

                app.logger.debug("User '%s' was created." % p_data['user'])

        else:
            app.logger.debug("LDAP authentication failed.")
    else:
        app.logger.debug("LDAP authentication deactivated.")

    # PHASE 2: database
    # Query user by nethz or email now

    # Complicated query, does the following: if user specified by nethz exists
    # import this way if not check by email
    if (app.data.driver.session.query(exists().where(
            models.User.nethz == p_data['user'])).scalar()):
        user = app.data.driver.session.query(models.User).filter_by(
            nethz=p_data['user']).one()
    elif (app.data.driver.session.query(exists().where(
            models.User.email == p_data['user'])).scalar()):
        user = app.data.driver.session.query(models.User).filter_by(
            email=p_data['user']).one()
    else:
        user = None  # Neither found by nethz nor email

    if user:
        app.logger.debug("User found in db.")
        if user.membership == "none":
            status = "Login failed. Membership is None!"
            app.logger.debug(status)
            abort(401, description=status)
        elif user.verify_password(p_data['password']):
            app.logger.debug("Login successful.")
            return send_response('sessions', _token_response(user.id))
        else:
            status = "Login failed: Password does not match!"
            app.logger.debug(status)
            abort(401, description=debug_error_message(status))

    # PHASE 2B: root user shortcut
    # if nethz is root, try to auth the root user
    if p_data['user'] == 'root':
        root = app.data.driver.session.query(models.User).filter_by(id=0).one()
        if root.verify_password(p_data['password']):
            app.logger.debug("Login as root successful.")
            return send_response('sessions', _token_response(0))

    # PHASE 3: Abort if everything else fails
    # LDAP is unsuccessful (deactivated/wrong credentials) and user not found
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
