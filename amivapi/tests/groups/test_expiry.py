# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test that expired group memberships are deleted."""

from datetime import timedelta
from freezegun import freeze_time

from amivapi.cron import run_scheduled_tasks
from amivapi.tests.utils import WebTestNoAuth


class GroupMembershipExpiry(WebTestNoAuth):
    """Test that members are removed from groups, when the membership has
    expired."""

    def test_expired_groupmembership_gets_removed(self):
        user = self.new_object('users')
        group = self.new_object('groups')

        with self.app.app_context(), freeze_time(
                "2016-01-01 00:00:00") as frozen_time:
            self.new_object('groupmemberships',
                            user=str(user['_id']),
                            group=str(group['_id']),
                            expiry='2016-01-03T00:00:00Z')

            frozen_time.tick(delta=timedelta(days=1))
            run_scheduled_tasks()

            self.assertEqual(
                self.app.data.driver.db['groupmemberships'].count_documents({}),
                1)

            frozen_time.tick(delta=timedelta(days=2))
            run_scheduled_tasks()

            self.assertEqual(
                self.app.data.driver.db['sessions'].count_documents({}), 0)
