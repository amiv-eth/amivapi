# -*- coding: utf-8 -*-
#
# AMIVAPI test_cron.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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

        cron.delete_expired_permissions(self.db, self.app.config)

        permissions = self.db.query(models.Permission).all()
        self.assertEquals(len(permissions), 1)
