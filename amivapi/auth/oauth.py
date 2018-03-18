"""Implement OAuth functionality.

We currently only support the implicit grant type. Client applications
redirect their users to the /oauth/authorize endpoint of the API. This will
serve the login page. After correct login or user confirmation (if logged in
already), the user is referred back to the client application.
"""

from urllib.parse import urlencode

from eve.methods.post import post_internal
from flask import (
    abort,
    Blueprint,
    current_app,
    g,
    redirect,
    render_template,
    request,
    url_for
)
from werkzeug.exceptions import Unauthorized

from amivapi.auth.auth import AdminOnlyAuth, authenticate_token
from amivapi.utils import register_domain
from amivapi.check_utils import check_str_nonempty


oauth_blueprint = Blueprint('oauth', __name__, template_folder='templates')


def append_url_params(url, params):
    """Add parameters to a url.

    Args:
        url(str): Existing URL.
        **params: Parameters to append.
    """
    if '?' not in url:
        url += '?'

    if url[-1] not in ['?', '&']:
        url += '&'

    return url + urlencode(params)


def validate_oauth_authorization_request(response_type, client_id,
                                         redirect_uri):
    """Validate an OAuth authentication request for an implicit grant.

    See https://tools.ietf.org/html/rfc6749#section-4.2.1

    Returns:
        The actual URL the client should be redirected to.
    """

    check_str_nonempty(response_type, "Missing response_type")
    check_str_nonempty(client_id, "Missing client_id")

    if response_type != 'token':
        abort(422, "response_type is not supported.")

    db = current_app.data.driver.db['oauthclients']
    client = db.find_one({'client_id': client_id})

    if not client:
        abort(422, "Unknown client_id")

    if not redirect_uri:
        redirect_uri = client['redirect_uri']

    if not redirect_uri.startswith(client['redirect_uri']):
        abort(422, "Redirect URI is not whitelisted!")

    return redirect_uri


@oauth_blueprint.route('/oauth/login', methods=['POST'])
def oauth_login():
    """Endpoint to receive user input from the login form."""
    response_type = request.form.get('response_type')
    client_id = request.form.get('client_id')
    redirect_uri = request.form.get('redirect_uri')
    scope = request.form.get('scope')
    state = request.form.get('state')

    # Check this is a proper oauth client
    redirect_uri = validate_oauth_authorization_request(
        response_type, client_id, redirect_uri)

    # Check we have login data
    token = request.cookies.get('token')
    try:
        if token:
            # In this case the user was logged in already and just accepted
            # the request.
            authenticate_token(token)
            if g.current_user is None:
                # Session ended since we served the login page. Back to login.
                # This is caught by the except below.
                abort(401)

        else:
            resp = post_internal(
                'sessions',
                {
                    'username': request.form.get('username'),
                    'password': request.form.get('password')
                }
            )[0]
            if 'token' not in resp:
                abort(401, "post_internal to sessions failed: %s" % resp)
            token = resp['token']

    except Unauthorized as e:
        # Login failed. Redirect back to the login page.
        error_msg = ("Login failed! If you think there is an error, please "
                     "contact AMIV with the exact time of your login.")
        current_app.logger.info("Login failed with error: %s" % e)
        login_url = url_for('.oauth_authorize',
                            response_type=response_type,
                            client_id=client_id,
                            redirect_url=redirect_uri,
                            scope=scope,
                            state=state,
                            error_msg=error_msg)
        response = current_app.make_response(redirect(login_url))
        response.set_cookie('token', '', expires=0)
        return response

    # We have a valid token! Let's bring the user back to the oauth client.
    redirect_uri = append_url_params(redirect_uri, {
        'access_token': token,
        'token_type': 'bearer',
        'scope': 'amiv',
        'state': state
    })
    response = current_app.make_response(redirect(redirect_uri))

    # Also save the token in the amivapi cookies, so fur further logins the
    # user only has to accept and not enter his credentials.
    response.set_cookie('token', token)
    return response


@oauth_blueprint.route('/oauth/authorize')
def oauth_authorize():
    """Endpoint for OAuth login. OAuth clients redirect users here."""
    response_type = request.args.get('response_type')
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    scope = request.args.get('scope')
    state = request.args.get('state')
    error_msg = request.args.get('error_msg')

    # Check this is a request by a proper client
    redirect_uri = validate_oauth_authorization_request(
        response_type, client_id, redirect_uri)

    # Check if the user already has a token
    token = request.cookies.get('token')
    authenticate_token(token)
    need_login = g.current_user is None

    # Serve the login page
    return render_template("loginpage.html",
                           response_type=response_type,
                           client_id=client_id,
                           redirect_uri=redirect_uri,
                           scope=scope,
                           state=state,
                           need_login=need_login,
                           error_msg=error_msg)


oauthclients_domain = {
    'oauthclients': {
        'description': "OAuth clients need to be registered on this resource "
                       "to be allowed to use the central login.",

        'public_methods': [],
        'public_item_methods': [],
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': AdminOnlyAuth,

        'schema': {
            'client_id': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'unique': True,
                'description': "Name of the OAuth client service. This is the "
                "name displayed to the user on login."
            },
            'redirect_uri': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'unique': True,
                'description': "Pattern for URLs this client may use for "
                "redirects. All URLs must start with this pattern, or the "
                "login will be denied. Make sure URLs that can be accepted do "
                "not allow further redirects to prevent phishing attacks that "
                "forward through your tool."
            }
        }
    }
}


def init_oauth(app):
    """Register oauthclient resource."""
    register_domain(app, oauthclients_domain)
    app.register_blueprint(oauth_blueprint)
