import hashlib
import json
import rsa
from os import urandom
from datetime import datetime
from base64 import b64encode, b64decode

from flask import current_app as app
from flask import Blueprint, abort, request

from eve.render import send_response
from eve.methods.post import post_internal
from eve.auth import TokenAuth

from sqlalchemy.orm.exc import NoResultFound

from models import User, Session

"""
This file provides token based authentification. A user can POST the /sessions
resource to obtain a token, which is a json dict of the following form:

{
    'user_id': integer,
    'login_time': time,
    'signature': string(64 bytes hex = 256 Bit SHA2)
}

This token shows that he is the user identified by user_id and obtained the
token at the time in login_time.
The signature is the SHA2 hash of user_id padded with zeros to 10 digits
followed by the time of login in the DATE_FORMAT specified in the config
followed by the servers login secret(see TokenAuth._create_signature)
"""


def _create_signature(user_id, login_time):
    msg = "{:0=10d}".format(user_id) \
          + login_time.strftime(app.config['DATE_FORMAT'])

    return b64encode(rsa.sign(msg, app.config['LOGIN_PRIVATE_KEY'], 'SHA-256'))


""" Creates a new hash for a password. This generates a random salt, so it can
not be used to check hashes!
"""


def create_new_hash(password):
    salt = urandom(16)
    return (
        b64encode(salt) +
        '$' +
        b64encode(hashlib.pbkdf2_hmac('SHA256', password, salt, 100000))
    )


""" Creates a new token for the specified user. The new token is based on the
current time, so the return value will change every second.
"""


def createToken(user_id):
    time = datetime.now()
    signature = _create_signature(user_id, time)

    return b64encode(json.dumps({
        'user_id': user_id,
        'login_time': time.strftime(app.config['DATE_FORMAT']),
        'signature': signature,
    }))


class TokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        dbsession = app.data.driver.session

        try:
            sess = dbsession.query(Session).filter(Session.token == token).one()
        except NoResultFound:
            abort(401)

        # this is used by eve for the _author field
        self.set_request_auth_value(sess.user_id)

        return True


""" Authentification related endpoints """

auth = Blueprint('auth', __name__)


""" Handle POST to /sessions

A POST to /sessions exspects a username and password. If they are correct a
token is created and used to register a session in the database, which is sent back to the user.

If the user is not found we try to import the user via LDAP, if he is found we update his data
"""


@auth.route('/sessions', methods=['POST'])
def process_login():
    user = app.data.driver.session.query(User).filter_by(
        username=request.form['username']).all()

    if(len(user) == 1):
        (salt, hashed_password) = user[0].password.split('$')
        salt = b64decode(salt)
        hashed_password = b64decode(hashed_password)

        if hashed_password != hashlib.pbkdf2_hmac(
                'SHA256',
                request.form['password'],
                salt,
                100000
        ):
            abort(401)

        token = createToken(user[0].id)
        response = post_internal(
            'sessions',
            {
                'user_id': user[0].id,
                'token': token
            }
        )
        return send_response('sessions', response)

    # Try to import user via ldap
    abort(501)


""" Auth related hooks """


""" Hooks to hash passwords when user entries are changed in the database """


def hash_password_before_insert(users):
    for u in users:
        u['password'] = create_new_hash(u['password'])


def hash_password_before_update(users):
    hash_password_before_insert(users)


def hash_password_before_replace(users, original_users):
    hash_password_before_insert(users)
