# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util


class PublicForwardTest(util.WebTest):

    def test_self_enroll_public_group(self):
        user = self.new_user()
        group = self.new_group(allow_self_enrollment=True)
        session = self.new_session(user_id=user.id)

        self.api.post("/groupmembers", data={
            'user_id': user.id,
            'group_id': group.id,
        }, token=session.token, status_code=201)

        group2 = self.new_group(allow_self_enrollment=False)

        # group 2 not visible
        self.api.post("/groupmembers", data={
            'user_id': user.id,
            'group_id': group2.id,
        }, token=session.token, status_code=422)
