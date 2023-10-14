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
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        # Check the response type must be token
        self.api.get(
            '/oauth?'
            'response_type=asdf'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool'
            '&state=xyz', status_code=422)

        # Check the whitelist for clients checks the client_id
        self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=OtherClient'
            '&redirect_uri=https://bla.org/tool'
            '&state=xyz', status_code=422)

        # Check only a correct URL is whitelisted
        self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.zomg/no'
            '&state=xyz', status_code=422)

    def test_relogin(self):
        """Test that a user that already has a token in his session
        automatically gets logged in again."""
        user = self.new_object('users')
        token = self.get_user_token(user['_id'])

        self.api.set_cookie('token', token, domain='localhost')
        login_page = self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        # As we have a valid token already it should not ask for a username
        # and password
        self.assertNotIn(b'Username: ', login_page.data)

        # Simulate sending the login form
        # The token is sent as cookie
        response = self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={'submit': 'confirm'},
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)

        parsed_url = urlsplit(response.location)
        self.assertEqual(parsed_url.scheme, 'https')
        self.assertEqual(parsed_url.netloc, 'bla.org')
        self.assertEqual(parsed_url.path, '/tool')

        query_params = dict(parse_qsl(parsed_url.query))
        self.assertEqual(query_params['a'], 'b')
        self.assertEqual(query_params['access_token'], token)
        self.assertEqual(query_params['token_type'], 'bearer')
        self.assertEqual(query_params['state'], 'xyz')

    def test_login(self):
        """Test that a user can login with username and password."""
        self.new_object('users', nethz='testuser', password='password')

        login_page = self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        # As we have a valid token already it should not ask for a username
        # and password
        self.assertIn(b'username', login_page.data)

        # Simulate sending the login form
        response = self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'username': 'testuser',
                'password': 'password'
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)

        parsed_url = urlsplit(response.location)
        self.assertEqual(parsed_url.scheme, 'https')
        self.assertEqual(parsed_url.netloc, 'bla.org')
        self.assertEqual(parsed_url.path, '/tool')

        query_params = dict(parse_qsl(parsed_url.query))
        self.assertEqual(query_params['a'], 'b')
        self.assertEqual(query_params['token_type'], 'bearer')
        self.assertEqual(query_params['state'], 'xyz')

        # Check the token works
        token = query_params['access_token']
        resp = self.api.get('/sessions?where={"token":"%s"}' % token,
                            token=token, status_code=200).json
        self.assertEqual(len(resp['_items']), 1)

    def test_login_wrong_data(self):
        """Test that wrong credentials lead back to oauth page."""
        self.new_object('users', nethz='testuser', password='password')

        # Simulate sending the login form
        self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'username': 'testuser',
                'password': 'wrongpass'
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=200)  # No redirect

        self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'username': 'notuser',
                'password': 'password'
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=200)  # No redirect

        self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'username': '',
                'password': ''
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=200)  # No redirect

    def test_remember(self):
        """Test that the token is saved as cookie if requested."""
        self.new_object('users', nethz='testuser', password='password')

        # By default, the token is not remembered
        response = self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'username': 'testuser',
                'password': 'password',
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)  # Expect redirect (successful auth)

        self.assertNotIn('Set-Cookie', response.headers)

        # If 'remember' is checked in the form, the token is saved as cookie
        response = self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'username': 'testuser',
                'password': 'password',
                'remember': 'remember',
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=302)  # Expect redirect (successful auth)

        # Get token from response
        query_params = dict(parse_qsl(urlsplit(response.location).query))
        token = query_params['access_token']

        # Verif
        self.assertTrue(response.headers['Set-Cookie']
                        .startswith('token=%s;' % token))

    def test_logout(self):
        """If a logout is submitted, the cookie is removed (set to '')"""
        response = self.api.post(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz',
            data={
                'submit': 'testuser',
            },
            headers={'content-type': 'application/x-www-form-urlencoded'},
            status_code=200)  # Go back to original page

        self.assertTrue(response.headers['Set-Cookie'].startswith('token=;'))

    def test_personal_greeting(self):
        """test that a logged in user will be greeted by firstname."""
        user = self.new_object('users', firstname='Pablito')
        token = self.get_user_token(user['_id'])

        self.api.set_cookie('token', token, domain='localhost')
        login_page = self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        self.assertIn(b'Hi Pablito!', login_page.data)

    def test_unpersonal_greeting(self):
        """Test that a not logged in user will be greeted generically."""
        login_page = self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        self.assertIn(b'Hello!', login_page.data)

    def test_client_id(self):
        """Test that the client id will be shown on the login page."""
        login_page = self.api.get(
            '/oauth?'
            'response_type=token'
            '&client_id=TestClient'
            '&redirect_uri=https://bla.org/tool?a=b'
            '&state=xyz', status_code=200)

        self.assertIn(b'TestClient', login_page.data)
