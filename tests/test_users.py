from unittest import TestCase
import requests, json

from common import apiurl, TestServer

class TestUser(TestCase):

    def test_create(self):

        # Run a development server while doing this unit test
        with TestServer() as server:

            # Create a user
            data = {'firstname': 'Lord', 'lastname': 'Gay', 'password':'gaygaygay', 'email':'lord@amiv.ethz.ch', 'gender':'male'}
            response = requests.post(apiurl + '/users', data)
            self.assertTrue(response.status_code == 201)
    

            # List users
            response = requests.get(apiurl + '/users')
            self.assertTrue(response.status_code == 200)

            users = json.loads(response.content)

            self.assertTrue(len(users['_items']) == 1)
            self.assertTrue(users['_items'][0]['firstname'] == 'Lord')
            self.assertTrue(users['_items'][0]['lastname'] == 'Gay')
            self.assertTrue(users['_items'][0]['password'] == 'gaygaygay')
            self.assertTrue(users['_items'][0]['email'] == 'lord@amiv.ethz.ch')
            self.assertTrue(users['_items'][0]['gender'] == 'male')

    def test_invalid_gender(self):
        with TestServer() as server:
            data = {'firstname': 'Lord', 'lastname': 'Gay', 'password':'gaygaygay', 'email':'lord@amiv.ethz.ch', 'gender':'trans'}
            response = requests.post(apiurl + '/users', data)
            self.assertTrue(response.status_code == 422)


    def test_invalid_email(self):
        with TestServer() as server:
            data = {'firstname': 'Lord', 'lastname': 'Gay', 'password':'gaygaygay', 'email':'no', 'gender':'male'}
            response = requests.post(apiurl + '/users', data)
            self.assertTrue(response.status_code == 201)

    

