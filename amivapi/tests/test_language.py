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
        data = {'title': {'language': 'Blorg',
                          'content': 'Blarg'}
                }

        raw_offer = self.api.post("/joboffers", data=data).json

        from pprint import pprint
        pprint(raw_offer)

        pprint(self.api.get("/joboffers/1").json)

        self.assertTrue(hasattr(raw_offer, 'title_id'))
        self.assertTrue(hasattr(raw_offer, 'description_id'))
        self.assertTrue(raw_offer.title_content == "")
        self.assertTrue(raw_offer.description_content == "")

        """session = self.new_session()
                                user = self.new_user(email=u"test@no.no")
                                user2 = self.new_user(email=u"looser92@gmx.com")
                                user3 = self.new_user(email=u"looser93@gmx.com")

                                forward = self.new_forward(address=u"test", is_public=True)

                                fuser = self.api.post("/forwardusers", data={
                                    'user_id': user.id,
                                    'forward_id': forward.id,
                                }, token=session.token, status_code=201).json

                                path = self.app.config['FORWARD_DIR'] + "/.forward+" + forward.address
                                with open(path, "r") as f:
                                    content = f.read()
                                    self.assertTrue(content == "test@no.no\n")

                                fuser2 = self.api.post("/forwardusers", data={
                                    'forward_id': forward.id,
                                    'user_id': user2.id,
                                }, token=session.token, status_code=201).json

                                print("fuser2:")
                                print(fuser2)

                                with open(path, "r") as f:
                                    content = f.read()
                                    self.assertTrue(content == "test@no.no\nlooser92@gmx.com\n")

                                self.api.patch("/forwardusers/%i" % fuser2['id'],
                                               data={'user_id': user3.id},
                                               headers={"If-Match": fuser2['_etag']},
                                               token=session.token,
                                               status_code=200)

                                with open(path, "r") as f:
                                    content = f.read()
                                    print content
                                    self.assertTrue(content == "test@no.no\nlooser93@gmx.com\n")

                                self.api.delete("/forwardusers/%i" % fuser['id'],
                                                token=session.token,
                                                headers={"If-Match": fuser['_etag']},
                                                status_code=204)

                                with open(path, "r") as f:
                                    content = f.read()
                                    self.assertTrue(content == "looser93@gmx.com\n")

                                self.api.delete("/forwards/%i" % forward.id, token=session.token,
                                                status_code=204)

                                self.assertTrue(exists(path) is False)
                        """
