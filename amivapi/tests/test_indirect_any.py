# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util
from amivapi.groups import Group


class IndirectAnyTest(util.WebTest):

    def test_indirect_any(self):
        user = self.new_user()
        group_mem = self.new_group()      # user is member
        self.new_group(moderator_id=user.id)  # user is moderator
        self.new_group()                  # user is unrelated

        self.new_group_member(user_id=user.id, group_id=group_mem.id)

        # Try to retrive all groups user is a member of
        my_groups = self.db.query(Group).filter(
            Group.indirect_any(u"members.user_id, %i" % user.id)).all()
        self.assertEqual(len(my_groups), 1)
        self.assertEqual(my_groups[0].id, group_mem.id)
