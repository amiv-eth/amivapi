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

from amivapi.models import Permission, Session, User
from amivapi.utils import get_config, mail, filter_ldap_data


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


def ldap_sync(db, config, ldap_connector):
    """ Select the n users from the database which have been updated last and
    query ldap to see if any information has changed.

    n  will be loaded from config entry 'LDAP_SYNC_COUNT'

    If there has never been an LDAP update, _synchronized will be set to None -
    those will be tried to be updated first

    :param db: The db session
    :param config: config dict
    """
    n_users = config['LDAP_SYNC_COUNT']

    # Get n users with nethz name not Null
    users = (
        db.query(User)
        .filter(User.nethz.isnot(None))
        .order_by(User._synchronized)
        [:n_users])

    # Create a dict for easy assignment later
    # Ignore users without nethz since they can not be queried

    # Prepare ldap query
    ldap_query = "(|"
    for user in users:
        ldap_query += "(cn=%s)" % user.nethz
    ldap_query += ")"

    # Query ldap
    ldap_res_raw = ldap_connector.search(ldap_query)
    # Put in dictionary with nethz as key for access
    ldap_res = {}
    for item in ldap_res_raw:
        filtered = filter_ldap_data(item)
        ldap_res[filtered['nethz']] = filtered

    # Now update users
    query_all = db.query(User)
    for user in users:
        # Filter for user
        query = query_all.filter_by(nethz=user.nethz)
        if user.nethz in ldap_res.keys():
            # No downgrade of membership
            if user.membership is not "none":
                ldap_res[user.nethz].pop('membership')

            query.update(ldap_res[user.nethz])
        else:
            # Still set _synchronized
            query.update({'_synchronized': datetime.utcnow()})

    # Finishing move
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
