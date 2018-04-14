"""Implement OAuth functionality.

We currently only support the implicit grant type. Client applications
redirect their users to the /oauth/authorize endpoint of the API. This will
serve the login page. After correct login or user confirmation (if logged in
already), the user is referred back to the client application.
"""

from urllib.parse import urlencode
from bson import ObjectId

from eve.methods.post import post_internal
from flask import (
    make_response,
    abort,
    Blueprint,
    current_app,
    g,
    redirect,
    render_template,
    request,
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


def oauth_redirect(redirect_uri, state):
    """Process login and redirect user.

    Loads and validates all inputs from request. First check if the request
    contains a cookie with token to use, otherwise check for login data in
    form.

    Returns:
        flask.Response: Flask redirect response

    Raises:
        werkzeug.exceptions.Unauthorized: If the user cannot be authorized
    """
    # First check for token in cookie
    token = request.cookies.get('token')
    if token:
        authenticate_token(token)
        if g.current_user is None:
            # Session ended since we served the login page. Back to login.
            # This is caught by the except below.
            abort(401, "Your session has expired, please log in again.")
    # Otherwise check for login data
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

    # We have a valid token! Let's bring the user back to the oauth client.
    redirect_uri = append_url_params(redirect_uri, {
        'access_token': token,
        'token_type': 'bearer',
        'scope': 'amiv',
        'state': state
    })

    # If the user wants to be remembered, save the token as cookie
    # so the next time only 'confirm' needs to be pressed
    response = current_app.make_response(redirect(redirect_uri))
    if request.form.get('remember'):
        response.set_cookie('token', token)
    return response


@oauth_blueprint.route('/oauth', methods=['GET', 'POST'])
def oauth():
    """Endpoint for OAuth login. OAuth clients redirect users here."""
    response_type = request.args.get('response_type')
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    state = request.args.get('state')
    token = request.cookies.get('token', '')
    error_msg = ''

    # Check this is a request by a proper client
    redirect_uri = validate_oauth_authorization_request(
        response_type, client_id, redirect_uri)

    # Check if the user already has a token
    authenticate_token(token)
    if g.current_user is None:
        user = None
    else:
        # Get first name for personal greeting
        query = {'_id': ObjectId(g.current_user)}
        projection = {'firstname': 1}  # Firstame is a required field for users
        data = current_app.data.driver.db['users'].find_one(query, projection)
        user = data['firstname']

    # Handle POST: Logout or Login+Redirect
    if request.method == 'POST':
        # Check if the user wants to log out
        logout = request.form.get('submit') == 'logout'
        if logout:
            # Reset token and user
            token = user = ''
        else:
            try:
                return oauth_redirect(redirect_uri, state)
            except Unauthorized as error:
                # Login failed. Set error message and reset token
                token = ''
                error_msg = ("Login failed! If you think there is an error, "
                             "please contact AMIV with the exact time of your "
                             "login.")
                current_app.logger.info("Login failed with error: %s" % error)

    # Serve the login page (reset cookie if needed)
    logo = current_app.config['LOGO_SVG']
    response = make_response(render_template("loginpage.html",
                                             client_id=client_id,
                                             logo=logo,
                                             user=user,
                                             error_msg=error_msg))
    response.set_cookie('token', token)
    return response


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
