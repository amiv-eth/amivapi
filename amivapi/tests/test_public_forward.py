from amivapi.tests import util


class PublicForwardTest(util.WebTest):

    def test_self_enroll_public_forward(self):
        user = self.new_user()
        forward = self.new_forward(is_public=True)
        session = self.new_session(user_id=user.id)

        self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward.id,
        }, token=session.token, status_code=201)

        forward2 = self.new_forward(is_public=False)

        self.api.post("/forwardusers", data={
            'user_id': user.id,
            'forward_id': forward2.id,
        }, token=session.token, status_code=403)
