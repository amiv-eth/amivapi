from amivapi.tests import util


class APIKeyTest(util.WebTest):

    def test_get_users_with_apikey(self):
        apikey = u"dsfsjkdfsdhkfhsdkfjhsdfjh"
        self.app.config['APIKEYS'][apikey] = {
            'name': 'Testkey',
            'users': {'GET': 1},
        }

        items = self.api.get(
            "/users", token=apikey, status_code=200).json['_items']

        # Can we see the root user?
        self.assertTrue(util.find_by_pair(items, "id", 0) is not None)
