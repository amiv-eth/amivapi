from amivapi.tests import util


class LanguageTest(util.WebTestNoAuth):

    def test_language(self):
        """ This test uses the /joboffers resource to check if the language
        fields work properly.
        Expected behaviours: POST to /jobofferss to get response:
        the response should contain a id that can be used to create
        translations
        POST to /translations can now create localized content
        Based on accepted languge, GET to /joboffers will now contain
        appropriate language content in a new created field
        Deleting should delete all translations as well
        """

        """Create Joboffer, should receive ID for translation of title and for
        description and they should obviously be different IDs"""
        data_offer = {'company': "AlexCorp"}

        response_offer = self.api.post("/joboffers", data=data_offer,
                                       status_code=201).json

        self.assertTrue('title_id' in response_offer.keys())
        self.assertTrue('description_id' in response_offer.keys())
        self.assertTrue('title_id' != 'description_id')

        """Create translations"""
        title_id = response_offer['title_id']
        desc_id = response_offer['description_id']

        data_de = {'localization_id': title_id,
                   'language': 'de',
                   'content': 'Ausgezeichnet!'}

        data_en = {'localization_id': title_id,
                   'language': 'en',
                   'content': 'Excellent!'}

        desc_de = {'localization_id': desc_id,
                   'language': 'de',
                   'content': 'Blablabla'}

        desc_en = {'localization_id': desc_id,
                   'language': 'en',
                   'content': 'Hurdurdur'}

        self.api.post("/translations", data=data_de, status_code=201)
        self.api.post("/translations", data=data_en, status_code=201)
        self.api.post("/translations", data=desc_de, status_code=201)
        self.api.post("/translations", data=desc_en, status_code=201)

        """Retrieve with Accept-Language Header for both languages"""
        header = {'Accept-Language': 'en'}

        response = self.api.get("/joboffers/1", headers=header,
                                status_code=200).json

        self.assertTrue('title' in response.keys())
        self.assertTrue(response['title'] == data_en['content'])
        self.assertTrue('description' in response.keys())
        self.assertTrue(response['description'] == desc_en['content'])

        header = {'Accept-Language': 'de'}

        response = self.api.get("/joboffers/1", headers=header,
                                status_code=200).json

        self.assertTrue('title' in response.keys())
        self.assertTrue(response['title'] == data_de['content'])
        self.assertTrue('description' in response.keys())
        self.assertTrue(response['description'] == desc_de['content'])

        """Remove event, translations should be deleted as well"""
        get_translations = self.api.get("/translations").json
        self.assertTrue(len(get_translations['_items']) == 4)

        h = {"If-Match": response_offer['_etag']}
        self.api.delete("/joboffers/1", headers=h)

        get_translations = self.api.get("/translations").json
        self.assertTrue(len(get_translations['_items']) == 0)

    def test_translation_without_match(self):
        """This test will try an accept header with a language where no
        translation is available.
        Should return result in default language"""

        self.app.config['DEFAULT_LANGUAGE'] = 'de'

        """Create Offer"""
        data_offer = {'company': "AlexCorp"}

        response_offer = self.api.post("/joboffers", data=data_offer,
                                       status_code=201).json

        self.assertTrue('title_id' in response_offer.keys())

        """Create translations"""
        id = response_offer['title_id']

        data_de = {'localization_id': id,
                   'language': 'de',
                   'content': 'Ausgezeichnet!'}

        self.api.post("/translations", data=data_de, status_code=201)

        """Retrieve with Accept-Language for unkown languages"""
        header = {'Accept-Language': 'br'}

        response = self.api.get("/joboffers/1", headers=header,
                                status_code=200).json

        self.assertTrue('title' in response.keys())
        self.assertTrue(response['title'] == data_de['content'])

    def test_translation_without_target(self):
        """This test will try to upload a translation without a language_id,
        should fail obviously"""
        data_de = {'localization_id': 42,  # it has to be 42. :D
                   'language': 'de',
                   'content': 'Ausgezeichnet!'}

        self.api.post("/translations", data=data_de, status_code=422)

    def test_same_langauge_twice(self):
        """This test will try to POST two different translations to the same
        field with two"""

        """Create Joboffer, should receive ID for translation of title"""
        data_offer = {'company': "AlexCorp"}

        response_offer = self.api.post("/joboffers", data=data_offer,
                                       status_code=201).json

        self.assertTrue('title_id' in response_offer.keys())

        """Create translation"""
        id = response_offer['title_id']

        data_de = {'localization_id': id,
                   'language': 'de',
                   'content': 'Ausgezeichnet!'}

        response_post = self.api.post("/translations", data=data_de,
                                      status_code=201).json

        """Test if patch and put are working properly"""
        data_de_alt = {'localization_id': id,
                       'language': 'de',
                       'content': 'Ausgezeichneter'}

        id = response_post['id']
        header = {'If-Match': response_post['_etag']}
        response_patch = self.api.patch("/translations/%i" % id,
                                        data=data_de_alt, headers=header,
                                        status_code=200).json

        header['If-Match'] = response_patch['_etag']
        response_put = self.api.put("/translations/%i" % id, data=data_de,
                                    headers=header, status_code=200).json

        """Now try to post same language again, should fail,
        Post not allowed if language exists
        """
        header['If-Match'] = response_put['_etag']
        self.api.post("/translations", data=data_de, status_code=405).json

    def test_no_translation(self):
        """No translation posted, title field should still be present and empty
        """
        data_offer = {'company': "AlexCorp"}

        self.api.post("/joboffers", data=data_offer,
                      status_code=201).json

        response = self.api.get("/joboffers/1", status_code=200).json

        self.assertTrue('title' in response.keys())

    def test_provide_id(self):
        """title and description id should not be accepted"""
        data_offer = {'company': "AlexCorp",
                      'title_id': 1}

        self.api.post("/joboffers", data=data_offer,
                      status_code=422)

        data_offer = {'company': "AlexCorp",
                      'description_id': 1}

        self.api.post("/joboffers", data=data_offer,
                      status_code=422)

        """The received ids should also not be patchable"""
        data_1 = {'company': 'AlexCorp'}
        data_2 = {'company': 'Hermanos Inc.'}

        r_1 = self.api.post("/joboffers", data=data_1, status_code=201).json
        r_2 = self.api.post("/joboffers", data=data_2, status_code=201).json

        # Using data from r_2 so that the ids are valid
        data_patch = {'title_id': r_2['title_id']}

        header = {'If-Match': r_1['_etag']}
        self.api.patch("/joboffers/%i" % r_1['id'], data=data_patch,
                       headers=header, status_code=422)

        data_patch = {'description_id': r_2['description_id']}

        header = {'If-Match': r_1['_etag']}
        self.api.patch("/joboffers/%i" % r_1['id'], data=data_patch,
                       headers=header, status_code=422)
