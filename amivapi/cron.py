from datetime import datetime

from amivapi.models import Permission, Session

"""
    Actions to be done on a regular basis. The run function should be executed
    once per day
"""


def delete_expired_sessions(db, config):
    timeout = config['SESSION_TIMEOUT']

    query = db.query(Session).\
        filter(Session._updated <= datetime.now() - timeout)

    for entry in query:
        db.delete(entry)

    db.commit()


def delete_expired_permissions(db):
    # warn people if it will expire in 14 days

    # TODO

    # delete permissions which are expired

    query = db.query(Permission).\
        filter(Permission.expiry_date <= datetime.now())

    for entry in query:
        db.delete(entry)

    db.commit()


"""
    Run cron tasks, this is called by manage.py
"""


def run(db, config):
    delete_expired_permissions(db)
    delete_expired_sessions(db, config)
