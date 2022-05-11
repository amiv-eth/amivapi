# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for user module.

Test if inactive non-members get deleted from database
"""

from freezegun import freeze_time

from amivapi.tests import utils
from amivapi.users import cleanup


class UserCleanupTest(utils.WebTest):
    """Test automatic User Cleanup"""

    def test_autodelete(self):
        cleanup_time = "2019-12-24T14:15:22Z"

        entries = [
            {
                # Non-member updated 6 months prior to cleanup.
                'membership': 'none',
                'updated': '2019-08-24T14:15:22Z'
            },
            {
                # Regular member updated 6 months prior to cleanup.
                'membership': 'regular',
                'updated': '2019-08-24T14:15:22Z'
            },
            {
                # Non-member updated 18 months prior to cleanup.
                # This use should be removed during cleanup.
                'membership': 'none',
                'updated': '2018-08-24T14:15:22Z'
            },
            {
                # Honorary member updated 18 months prior to cleanup.
                'membership': 'honorary',
                'updated': '2018-08-24T14:15:22Z'
            }
        ]

        root_token = self.get_root_token()

        with self.app.app_context():
            for idx, entry in enumerate(entries):
                with freeze_time(entry.get('updated')):
                    user = {
                        'nethz': f'pabloamiv{str(idx)}',
                        'firstname': 'Pablo',
                        'lastname': "AMIV",
                        'email': f'pablo{str(idx)}@amiv.ch',
                        'gender': 'male',
                        'membership': entry.get('membership')
                    }
                    self.api.post("/users", data=user, token=root_token)

            users = self.api.get("/users", token=root_token).json
            self.assertEqual(len(users['_items']), 4)

            with freeze_time(cleanup_time):
                cleanup.remove_inactive_users()

            users = self.api.get("/users", token=root_token).json

        self.assertEqual(len(users['_items']), 3)
