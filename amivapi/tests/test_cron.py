# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from datetime import datetime

from amivapi.tests import util
from amivapi import models, cron


class CronTest(util.WebTestNoAuth):
    def test_expired_sessions(self):
        self.new_session(user_id=0, _updated=datetime(2010, 1, 1))
        self.new_session(user_id=0, _updated=datetime.utcnow())

        cron.delete_expired_sessions(self.db, self.app.config)

        sessions = self.db.query(models.Session).all()
        self.assertEquals(len(sessions), 1)

    def test_cron_run(self):
        """ This test verifies that the methods are actually called when
        running cron.py

        If we add more methods to cron, put them in here.

        But it would actually be better to test the script part of cron
        (if __name__ == __main__: ... ), I dont know how to do this properly
        """
        # run() calls delete_expired_sessions
        class MethodLogger(object):
            def __init__(self, method):
                self.method = method
                self.was_called = False

            def __call__(self, *args, **kvargs):
                self.method(*args, **kvargs)
                self.was_called = True

        run = MethodLogger(cron.run)

        run(self.db, self.app.config)

        self.assertTrue(run.was_called)
