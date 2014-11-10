from amivapi.tests import util


class SessionResourceTest(util.WebTest):

    def test_collection(self):
        groups = [self.new_group() for _ in range(5)]

        resp = self.api.get("/groups", status_code=200)
        self.assertTrue(len(resp.json['_items']), len(groups))
