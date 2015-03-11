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

    def test_expired_permissions(self):
        self.new_permission(user_id=0, role='vorstand',
                            expiry_date=datetime(2010, 1, 1))
        self.new_permission(user_id=0, role='vorstand',
                            expiry_date=datetime.utcnow() + timedelta(1, 0, 0))

        cron.delete_expired_permissions(self.db)

        permissions = self.db.query(models.Permission).all()
        self.assertEquals(len(permissions), 1)
