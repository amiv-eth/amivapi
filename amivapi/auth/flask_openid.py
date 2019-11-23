"""Flask endpoints to implement OpenID login."""

from flask import (
    abort,
    current_app,
    Blueprint,
    redirect,
    request,
    url_for
)

from amivapi.auth.openid_client import OpenIDClient

openid_blueprint = Blueprint('openid', __name__)


class MongoPutPopStore:
    """Object that allows storing simple key value pairs in a mongo DB."""

    def __init__(self, collection):
        self._collection = collection

    def put(self, key, value):
        self._collection.insert_one({'key': key, 'value': value})

    def pop(self, key):
        entry = self._collection.find_one_and_delete({'key': key})
        if entry is None:
            return None
        return entry['value']


@openid_blueprint.route('/openid_callback', methods=['GET'])
def openid_callback():
    external_callback_url = url_for('openid_callback', _external=True)
    current_app.openid_client.execute_callback(
        request.args, external_callback_url)


@openid_blueprint.route('/openid_login', methods=['GET'])
def openid_login():
    """Endpoint that kicks off login through the OpenID provider."""
    redirect_uri = request.args.get('redirect_uri')
    if not redirect_uri:
        abort(400, 'Missing redirect URI')
    external_callback_url = url_for('openid_callback', _external=True)
    auth_url = current_app.openid_client.make_auth_redirect(
        redirect_uri, external_callback_url)
    return current_app.make_response(redirect(auth_url))


def init_app(app):
    client_id = app.config['SIP_AUTH_AMIVAPI_CLIENT_ID']
    client_secret = app.config['SIP_AUTH_AMIVAPI_CLIENT_SECRET']
    discovery_url = app.config['SIP_AUTH_OIDC_DISCOVERY_URL']
    if not client_id and not client_secret and not discovery_url:
        # OpenID disabled.
        return

    if not client_id:
        raise ValueError('Missing SIP_AUTH_AMIVAPI_CLIENT_ID in API config.')
    if not client_secret:
        raise ValueError(
            'Missing SIP_AUTH_AMIVAPI_CLIENT_SECRET in API config.')
    if not discovery_url:
        raise ValueError('Missing SIP_AUTH_OIDC_DISCOVERY_URL in API config.')

    with app.app_context():
        openid_state_collection = app.data.driver.db['openid_state']
    openid_state_store = MongoPutPopStore(openid_state_collection)
    app.openid_client = OpenIDClient(
        discovery_url=app.config['SIP_AUTH_OIDC_DISCOVERY_URL'],
        client_id=client_id,
        client_secret=client_secret,
        state_store=openid_state_store)
