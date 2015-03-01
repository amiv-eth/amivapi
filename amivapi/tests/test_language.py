from amivapi.tests import util


class LanguageTest(util.WebTestNoAuth):

    def test_language(self):
        """ This test uses the /joboffers resource to check if the language
        fields work properly.
        Expected behaviours: POST to /jobofferss to get responve
        the response should contain empty language fields (title and descption)
        and id that can be used to create translations
        POST to /translations can now receive translated content
        Based on accepted languge, GET to /joboffers will now contain
        appropriate language content
        """
        from pprint import pprint

        # pprint(self.api.get("/").json)

        data = {'company': 'AlonCorp',
                'title': {'en': 'yolo',
                          'de': 'Blarg'}
                }

        raw_offer = self.api.post("/joboffers", data=data).json

        pprint(raw_offer)
        print('---')
        pprint(self.api.get("/joboffers").json)
        print('---')
        pprint(self.api.get("/translations").json)
