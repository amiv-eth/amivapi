#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
Actions to be done on a regular basis. The run function should be executed
once per day
"""


from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from amivapi.models import Session
from amivapi.utils import get_config

from amivapi.ldap import ldap_synchronize


def delete_expired_sessions(db, config):
    """ Delete expired sessions

    :param db: The db session
    :param config: Config dict
    """
    timeout = config['SESSION_TIMEOUT']

    query = db.query(Session).filter(
        Session._updated <= datetime.utcnow() - timeout)

    for entry in query:
        db.delete(entry)

    db.commit()


def run(db, config):
    """ Run cron tasks

    :param db: The db session
    :param config: The config dict
    """
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
