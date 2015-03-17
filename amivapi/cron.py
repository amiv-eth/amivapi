#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# AMIVAPI cron.py
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

"""
Actions to be done on a regular basis. The run function should be executed
once per day
"""


from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from amivapi.models import Permission, Session
from amivapi.utils import get_config, mail


def delete_expired_sessions(db, config):
    """ Delete expired sessions

    :param db: The db session
    :param config: Config dict
    """
    timeout = config['SESSION_TIMEOUT']

    query = db.query(Session).filter(
        Session._updated <= datetime.now() - timeout)

    for entry in query:
        db.delete(entry)

    db.commit()


def delete_expired_permissions(db, config):
    """ Delete expired permissions and warn users if their permissions will
    expire in 14 days per mail

    :param db: The db session
    :param config: config dict
    """
    # warn people if it will expire in 14 days
    query = db.query(Permission).filter(
        Permission.expiry_date <= datetime.now() + timedelta(days=14),
        Permission.expiry_date >= datetime.now() + timedelta(days=13))

    for entry in query:
        text = (config['PERMISSION_EXPIRED_WARNMAIL_TEXT']
                % dict(name=entry.user.firstname, role=entry.role,
                       admin_mail=config['ROOT_MAIL']))
        subject = (config['PERMISSION_EXPIRED_WARNMAIL_SUBJECT']
                   % dict(role=entry.role))

        mail(config['ROOT_MAIL'], [entry.user.email], subject, text)

    # delete permissions which are expired

    query = db.query(Permission).filter(
        Permission.expiry_date <= datetime.now())

    for entry in query:
        db.delete(entry)

    db.commit()


def run(db, config):
    """ Run cron tasks

    :param db: The db session
    :param config: The config dict
    """
    delete_expired_permissions(db, config)
    delete_expired_sessions(db, config)


# Run


if __name__ == '__main__':
    cfg = get_config()

    engine = create_engine(cfg['SQLALCHEMY_DATABASE_URI'])
    sessionmak = sessionmaker(bind=engine)
    session = sessionmak()

    run(session, cfg)
