#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
Actions to be done on a regular basis. The run function should be executed
once per day
"""


from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from amivapi.models import Permission, Session
from amivapi.utils import get_config, mail

from amivapi.ldap import ldap_synchronize


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

    if config['ENABLE_LDAP']:
        ldap_synchronize(config['LDAP_USER'],
                         config['LDAP_PASS'],
                         db,
                         config['LDAP_MEMBER_OU_LIST'])

# Run

if __name__ == '__main__':
    cfg = get_config()

    engine = create_engine(cfg['SQLALCHEMY_DATABASE_URI'])
    sessionmak = sessionmaker(bind=engine)
    session = sessionmak()

    run(session, cfg)
