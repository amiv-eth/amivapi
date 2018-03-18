# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test the oauth functions."""

from urllib.parse import urlsplit, parse_qsl

from amivapi.tests.utils import WebTest


class OAuthTest(WebTest):
    def setUp(self):
        super().setUp()
        self.new_object('oauthclients', client_id="TestClient",
                        redirect_uri="https://bla.org/tool")
        self.new_object('oauthclients', client_id="TestClient2",
                        redirect_uri="https://bla.zomg/no")

    def test_validation(self):
        """Test that the oauth authorize endpoint only accepts requests
        made from correct clients."""
        self.api.get(
            '/oauth/authorize?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        # Check the response type must be token
        self.api.get(
            '/oauth/authorize?'
            'response_type=asdf'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool'
            '&state=xyz', status_code=422)

        # Check the whitelist for clients checks the client_id
        self.api.get(
            '/oauth/authorize?'
            'response_type=token'
            '&client_id=OtherClient'
            '&redirect_uri=https://bla.org/tool'
            '&state=xyz', status_code=422)

        # Check only a correct URL is whitelisted
        self.api.get(
            '/oauth/authorize?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.zomg/no'
            '&state=xyz', status_code=422)

    def test_relogin(self):
        """Test that a user that already has a token in his session
        automatically gets logged in again."""
        user = self.new_object('users')
        token = self.get_user_token(user['_id'])

        self.api.set_cookie('localhost', 'token', token)
        login_page = self.api.get(
            '/oauth/authorize?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        # As we have a valid token already it should not ask for a username
        # and password
        assert b'Username: ' not in login_page.data

        # Simulate sending the login form
        response = self.api.post(
            '/oauth/login', data={
                'response_type': 'token',
                'client_id': 'TestClient',
                'redirect_uri': 'https://bla.org/tool?a=b',
                'state': 'xyz'
            }, headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)

        parsed_url = urlsplit(response.location)
        assert parsed_url.scheme == 'https'
        assert parsed_url.netloc == 'bla.org'
        assert parsed_url.path == '/tool'

        query_params = dict(parse_qsl(parsed_url.query))
        assert query_params['a'] == 'b'
        assert query_params['access_token'] == token
        assert query_params['token_type'] == 'bearer'
        assert query_params['state'] == 'xyz'

    def test_login(self):
        """Test that a user can login with username and password."""
        user = self.new_object('users', nethz='testuser', password='pass')
        token = self.get_user_token(user['_id'])

        login_page = self.api.get(
            '/oauth/authorize?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        # As we have a valid token already it should not ask for a username
        # and password
        assert b'Username: ' in login_page.data

        # Simulate sending the login form
        response = self.api.post(
            '/oauth/login', data={
                'response_type': 'token',
                'client_id': 'TestClient',
                'redirect_uri': 'https://bla.org/tool?a=b',
                'state': 'xyz',
                'username': 'testuser',
                'password': 'pass'
            }, headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)

        parsed_url = urlsplit(response.location)
        assert parsed_url.scheme == 'https'
        assert parsed_url.netloc == 'bla.org'
        assert parsed_url.path == '/tool'

        query_params = dict(parse_qsl(parsed_url.query))
        assert query_params['a'] == 'b'
        assert query_params['token_type'] == 'bearer'
        assert query_params['state'] == 'xyz'

        # Check the token works
        token = query_params['access_token']
        resp = self.api.get('/sessions?where={"token":"%s"}' % token,
                            token=token, status_code=200).json
        assert len(resp['_items']) == 1

    def test_login_wrong_data(self):
        """Test that wrong credentials lead to a redirect to the login form
        again."""
        self.new_object('users', nethz='testuser', password='pass')

        # Simulate sending the login form
        response = self.api.post(
            '/oauth/login', data={
                'response_type': 'token',
                'client_id': 'TestClient',
                'redirect_uri': 'https://bla.org/tool?a=b',
                'state': 'xyz',
                'username': 'testuser',
                'password': 'wrongpass'
            }, headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)

        assert '/oauth/authorize' in response.location
