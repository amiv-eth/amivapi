from os.path import exists

from amivapi.tests import util


class ForwardBackendTest(util.WebTestNoAuth):

    def test_forward_creation(self):
        session = self.new_session()
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
