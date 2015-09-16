# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util
from amivapi.settings import DATE_FORMAT

import datetime as dt


class PermissionValidationTest(util.WebTestNoAuth):
    """This test checks the custom validation concerning permissions"""
    def test_invalid_expiry_date(self):
        """This test is for expiry date validation"""
        # make new user
        user = self.new_user()
        userid = user.id

        # make new permission assignment with expiry  date in the past
        expiry = dt.datetime(2000, 11, 11)
        self.api.post("/permissions", data={
            'user_id': userid,
            'role': 'vorstand',
            'expiry_date': expiry.strftime(DATE_FORMAT),
        }, status_code=422)

        # make new permission assignment with right data
        expiry = dt.datetime(4200, 11, 11)
        self.api.post("/permissions", data={
            'user_id': userid,
            'role': 'vorstand',
            'expiry_date': expiry.strftime(DATE_FORMAT),
        }, status_code=201)

        # No expiry date should not be possible
        expiry = dt.datetime(4200, 11, 11)
        self.api.post("/permissions", data={
            'user_id': userid,
            'role': 'vorstand',
        }, status_code=422)

    def test_invalid_role(self):
        """This test tries to post with a nonexistent role"""
        user = self.new_user()
        userid = user.id

        data = {
            'user_id': userid,
            'role': 'They see me role-in, they hatin',
            'expiry_date': dt.datetime(9001, 1, 1).strftime(DATE_FORMAT)
        }
        self.api.post("/permissions", data=data, status_code=422)

        data['role'] = 'vorstand'
        self.api.post("/permissions", data=data, status_code=201)
