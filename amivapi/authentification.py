"""
This file provides token based authentification(identification of users). A
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
from eve.render import send_response
from eve.utils import debug_error_message, config

from sqlalchemy.orm.exc import NoResultFound

from amivapi.utils import create_new_hash, check_hash
from amivapi import models


class TokenAuth(TokenAuth):
    """ We could have used eve's allowed_roles parameter, but that does not
    support roles on endpoint level, but only on resource level"""
    def check_auth(self, token, allowed_roles, resource, method):
        """ This is the authentification function called by eve. It will parse
        the send token and determine if it is from a valid user or a know
        apikey.

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


authentification = Blueprint('authentification', __name__)


@authentification.route('/sessions', methods=['POST'])
def process_login():
    """ Login
    A POST to /sessions exspects a username and password. If they are correct a
    token is created and used to register a session in the database, which is
    sent back to the user.

    If the user is not found we try to import the user via LDAP, if he is found
    we update his data

    :returns: Flask.Response object
    """
    p_data = payload()
    if 'username' not in p_data:
        abort(422, description=debug_error_message(
            "Please provide a username."))
    if 'password' not in p_data:
        abort(422, description=debug_error_message(
            "Please provide the password."))

    user = app.data.driver.session.query(models.User).filter_by(
        username=p_data['username']).all()

    if(len(user) == 1):

        if not check_hash(p_data['password'], user[0].password):
            error = "Wrong login: Password does not match!"
            app.logger.debug(error)
            abort(401, description=debug_error_message(error))

        token = b64encode(urandom(256))
        # Make sure token is unique
        while app.data.driver.session.query(models.Session).filter_by(
                token=token).count() != 0:
            token = b64encode(urandom(256))

        response = post_internal(
            'sessions',
            {
                'user_id': user[0].id,
                'token': token
            }
        )
        return send_response('sessions', response)

    error = "Wrong login: User not found!"

    app.logger.debug(error)
    abort(401, description=debug_error_message(error))


#
#
# Hooks to hash passwords when user entries are changed in the database
#
#


def hash_password_before_insert(users):
    """ Hook to hash the password when a new user is inserted into the
    database """
    for u in users:
        if 'password' in u:
            u['password'] = create_new_hash(u['password'])


def hash_password_before_update(user, original_user):
    """ Hook to hash the password when it is changed """
    hash_password_before_insert([user])


def hash_password_before_replace(user, original_user):
    """ Hook to hash the password when a user is replaced with a new one """
    hash_password_before_insert([user])


#
#
# Hooks to add _author field to all database inserts
#
#


def set_author_on_insert(resource, items):
    """ Hook to set the _author field for all new objects """
    _author = getattr(g, 'logged_in_user', -1)
    for i in items:
        i['_author'] = _author


def set_author_on_replace(resource, item, original):
    """ Hook to set the _author field when a new object is inserted
    during a PUT request """
    set_author_on_insert(resource, [item])
