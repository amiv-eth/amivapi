from flask import Blueprint, abort, request
import json
from datetime import datetime
import hashlib
from datetime import timedelta
from flask import current_app as app
import rsa
from base64 import b64encode, b64decode

from models import User, Session
from eve.render import send_response
from eve.methods.post import post_internal


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


def createToken(user_id):
    time = datetime.now()
    signature = _create_signature(user_id, time)

    # Don't confuse database session and Session objects of the data model!
#    session = Session(user_id=user_id, signature=signature)
#    app.data.driver.session.add(session)
#    app.data.driver.session.commit()

    return b64encode(json.dumps({
        'user_id': user_id,
        'login_time': time.strftime(app.config['DATE_FORMAT']),
        'signature': signature,
    }))


class TokenAuth:

    def __init__(self, token):

        self.token = json.loads(token)
        self.user_id = self.token['user_id']

        self.time = datetime.strptime(
            self.token['login_time'],
            app.config['DATE_FORMAT']
            )

        # Log out if login_time is too far in the past
        if datetime.now() > self.time + timedelta(seconds=app.config['LOGIN_TIMEOUT']):
            abort(419)

        self.signature = self._create_signature(self.user_id, self.time)

        if self.signature != self.token['signature']:
            abort(401)

        # Check if token is in database
        if models.Session.query \
                .filter_by(signature=self.signature, user_id=self.user_id) \
                .count() != 1:
            abort(401)

    def deleteToken(self):
        session = models.Session.query \
            .filter_by(signature=self.signature) \
            .first()

        db.session.delete(session)
        db.session.commit()


login = Blueprint('login', __name__)

@login.route('/sessions', methods=['POST'])
def process_login():
    user = app.data.driver.session.query(User).filter_by(
        username=request.form['username'],
        password=request.form['password']).all()

    if len(user) == 1:
        # User is in database, log in
        token = createToken(user[0].id)
        response = post_internal('sessions',
                {
                    'user_id': user[0].id,
                    'token': token
                })
        return send_response('sessions', response)

    # Try to import user via ldap
    abort(501)


