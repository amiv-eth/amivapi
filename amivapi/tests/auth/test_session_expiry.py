#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

""" Test that sessions get cleaned up after enough time passed. """

from datetime import timedelta
from freezegun import freeze_time

from amivapi.tests.utils import WebTest
from amivapi.cron import run_scheduled_tasks


class TestSessionExpiry(WebTest):
    def test_session_expiry(self):
        with self.app.app_context(), freeze_time(
                "2016-01-01 00:00:00") as frozen_time:
            self.new_object("users", nethz="pablo", password="pass")
            self.api.post('/sessions',
                          data={"username": "pablo", "password": "pass"},
                          status_code=201)

            frozen_time.tick(delta=self.app.config['SESSION_TIMEOUT'] -
                             timedelta(days=1))
            run_scheduled_tasks()

            self.assertEqual(self.app.data.driver.db['sessions'].find().count(),
                             1)

            frozen_time.tick(delta=timedelta(days=2))
            run_scheduled_tasks()

            self.assertEqual(self.app.data.driver.db['sessions'].find().count(),
                             0)
