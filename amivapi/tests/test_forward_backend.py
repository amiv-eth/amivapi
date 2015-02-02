from os.path import exists

from amivapi.tests import util


class ForwardBackendTest(util.WebTestNoAuth):

    def test_forward_creation(self):
        session = self.new_session()
        user = self.new_user(email=u"test@no.no")

        forward = self.new_forward(address=u"test", is_public=True)

        fuser = self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward.id,
        }, token=session.token, status_code=201).json

        path = self.app.config['FORWARD_DIR'] + "/.forward+" + forward.address
        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "test@no.no\n")

        faddr = self.api.post("/forwardaddresses", data={
            'forward_id': forward.id,
            'address': "looser92@gmx.com",
        }, token=session.token, status_code=201).json

        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "test@no.no\nlooser92@gmx.com\n")

        self.api.patch("/forwardaddresses/" + faddr['id'],
                       data={'address': "looser93@gmx.com"},
                       headers={"If-Match": faddr['etag']},
                       token=session.token,
                       status_code=200)

        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "test@no.no\nlooser93@gmx.com\n")

        self.api.delete("/forwardusers/" + fuser['id'],
                        token=session.token, status_code=204)

        with open(path, "r") as f:
            content = f.read()
            self.assertTrue(content == "looser93@gmx.com\n")

        self.api.delete("/forwards/" + forward.id, token=session.token,
                        status_code=204)

        self.assertTrue(exists(path) is False)
