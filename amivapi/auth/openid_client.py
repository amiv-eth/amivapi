"""A simple client for OpenID in the 'code' flow mode."""

import json
from urllib.parse import urlencode

from jwcrypto import jwk, jwt
import requests

from amivapi.utils import token_urlsafe


def _load_json_from_url(url):
    http_response = requests.get(url)
    if http_response.status_code != 200:
        raise ValueError(
            'Error when loading json from URL: %s. Response: %i, %s'
            % (url, http_response.status_code, http_response.text))
    try:
        return json.loads(http_response.text)
    except json.decoder.JSONDecodeError as e:
        raise ValueError(
            'Response could not be parsed as JSON! '
            'Error: %s, content: %s' % (e, http_response.text))


class OpenIDError(Exception):
    pass


class OpenIDClient:
    """A simple OpenID client that implements the 'code' flow.

    See https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth
    """

    def __init__(self, discovery_url, client_id, client_secret,
                 state_store):
        self._state_store = state_store
        self._client_id = client_id
        self._client_secret = client_secret
        self._config = _load_json_from_url(discovery_url)
        provider_json_web_key_cfg = _load_json_from_url(
            self._config['jwks_uri'])
        self._provider_json_web_key = jwk.JWK(**provider_json_web_key_cfg)

    def fetch_tokens(self, code, external_callback_url):
        token_response = requests.post(
            self._config['token_endpoint'],
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': external_callback_url,
            })
        token_response_json = json.loads(token_response.text)
        if token_response.status_code != 200:
            raise OpenIDError(
                'Error fetching token: %s' %
                token_response_json.get('error', 'Unknown error'))
        if token_response_json.get('token_type') != 'Bearer':
            raise OpenIDError(
                'Invalid token type received from OpenID provider.')

        access_token = token_response_json.get('access_token')
        id_token = token_response_json.get('id_token')
        return access_token, id_token

    def decode_token(self, token):
        return jwt.JWT(key=self._provider_json_web_key, jwt=token)

    def make_auth_redirect(self, final_redirect_uri, external_callback_url):
        # Sanity check the return URL.
        if not final_redirect_uri or not final_redirect_uri.startswith('http'):
            raise OpenIDError('Invalid or missing redirect URL! Value: %s'
                              % final_redirect_uri)

        if not external_callback_url.startswith('https://'):
            raise OpenIDError(
                'Bad OpenID configuration! Callback URL does not seem to be '
                'https: %s' % external_callback_url)

        # This key is both used to later reconstruct the context of this call
        # (which is basically `final_redirect_uri`) as well as a protection
        # against CSRF attacks. This key should be hard to guess, as it is
        # identifying this authentication flow.
        state_key = token_urlsafe()
        # We will need to know where to send the client when we are finished.
        self._state_store.put(state_key, final_redirect_uri)

        query_params = {}
        query_params['scope'] = 'openid'
        query_params['response_type'] = 'code'
        query_params['client_id'] = self._client_id
        query_params['redirect_uri'] = external_callback_url
        query_params['state'] = state_key
        base_url = self._config['authorization_endpoint']
        query_string = urlencode(query_params)
        return f'{base_url}?{query_string}'

    def execute_callback(self, query_params):
        state_key = query_params['state']
        final_redirect_uri = self._state_store.pop(state_key)
        if not final_redirect_uri:
            raise OpenIDError('Unknown authentication state.')

        if 'code' in query_params:
            access_token, id_token = self.fetch_tokens(query_params['code'])
            user_info = self.decode_token(id_token)
            print(user_info)
            raise OpenIDError(str(user_info))

        else:
            raise OpenIDError(
                'Authorization with external provider failed.\nCode: %i\n'
                'Description: %s\nURI: %s'
                % (query_params.get('error'),
                   query_params.get('error_description'),
                   query_params.get('error_uri')))
