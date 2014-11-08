from unittest import TestCase
import requests

from common import apiurl, TestServer


class TestSession(TestCase):

    def test_login(self):

        # Run a development server while doing this unit test
        with TestServer():

            # Create a user by mail
            data = {'firstname': 'Lord',
                    'lastname': 'Gay',
                    'password': 'gaygaygay',
                    'email': 'lord@amiv.ethz.ch',
                    'gender': 'male'}
            r = requests.post(apiurl + '/users', data)
            self.assertTrue(r.status_code == 201)

            # Try to login with the user
            data = {'username': 'lord@amiv.ethz.ch',
                    'password': 'gaygaygay'}
            r = requests.post(apiurl + '/sessions', data)
            self.assertTrue(r.status_code == 201)
