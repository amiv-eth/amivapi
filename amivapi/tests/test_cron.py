# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from datetime import datetime, timedelta

from amivapi.tests import util
from amivapi import models, cron


class CronTest(util.WebTestNoAuth):
    def test_expired_sessions(self):
        self.new_session(user_id=0, _updated=datetime(2010, 1, 1))
        self.new_session(user_id=0, _updated=datetime.utcnow())

        cron.delete_expired_sessions(self.db, self.app.config)

        sessions = self.db.query(models.Session).all()
        self.assertEquals(len(sessions), 1)
