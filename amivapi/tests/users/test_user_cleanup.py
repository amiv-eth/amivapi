# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for user module.

Test if inactive non-members get deleted from database
"""

from datetime import datetime, timedelta
from lib2to3.pgen2 import token
from signal import SIG_DFL
from freezegun import freeze_time

from amivapi import cron
from amivapi.tests import utils
from amivapi.users import cleanup



class UserCleanupTest(utils.WebTest):
    """Test automatic User Cleanup"""

    def test_autodelete(self):
        entries = [
            {
                'nethz': 'pablamiv',
                'firstname': "Pabla",
                'lastname': "AMIV",
                'email': "pabla@amiv.ch",
                'gender': 'male',
                'membership': 'none'
            },
            {
                'nethz': 'pablomiv',
                'firstname': "Pablo",
                'lastname': "AMIV",
                'email': "pablo@amiv.ch",
                'gender': 'male',
                'membership': "regular"
            },
            {
                'nethz': 'pablemiv',
                'firstname': "Pable",
                'lastname': "AMIV",
                'email': "pable@amiv.ch",
                'gender': 'male',
                'membership': "none"
            },
            {
                'nethz': 'pablimiv',
                'firstname': "Pabli",
                'lastname': "AMIV",
                'email': "pabli@amiv.ch",
                'gender': 'male',
                'membership': "honorary"
            }
        ]

        root_token = self.get_root_token()
        
        with self.app.app_context():
            with freeze_time("2019-08-24T14:15:22Z"):
                # Non-member, updated 6 Month ago
                self.api.post("/users", data=entries[0], token=root_token)
                # Member, updated 6 Month ago
                self.api.post("/users", data=entries[1], token=root_token)

            with freeze_time("2018-08-24T14:15:22Z"):
                # Non-member, updated 18 Month ago (should be deleted)
                self.api.post("/users", data=entries[2], token=root_token)
                # (honorary) Member, updated 18 Month ago
                self.api.post("/users", data=entries[3], token=root_token)

            users = self.api.get("/users", token=root_token ).json
            self.assertEqual(len(users['_items']), 4)

            with freeze_time("2019-12-24T14:15:22Z"):
                cleanup.remove_inactive_users()

            users = self.api.get("/users", token=root_token ).json

        self.assertEqual(len(users['_items']), 3)
