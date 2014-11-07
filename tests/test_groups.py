from unittest import TestCase
import requests, json

from common import apiurl, TestServer

class TestGroup(TestCase):

    def test_create(self):

        # Run a development server while doing this unit test
        with TestServer() as server:
            
            # Create some users
            for i in range(1,5):
                data = {'firstname': 'first'+str(i), 'lastname': 'last'+str(i), 'password':'gaygaygay', 'email':'user'+str(i)+'@amiv.ethz.ch', 'gender':'male'}
                response = requests.post(apiurl + '/users', data)
                self.assertTrue(response.status_code == 201)

            # Create some groups
            for i in range(1,5):
                data = {'name': 'group'+str(i)}
                response = requests.post(apiurl + '/groups', data)
                self.assertTrue(response.status_code == 201)

            # Get the groups
            response = requests.get(apiurl + '/groups')
            self.assertTrue(response.status_code == 200)
            groups = json.loads(response.content)
            self.assertTrue(len(groups['_links']) == 4)
            

