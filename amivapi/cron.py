#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Actions to be done on a regular basis.

The run function should be executed once per day
"""
from datetime import datetime

from flask import current_app

from amivapi.bootstrap import create_app
from amivapi.models import Session
from amivapi.ldap import ldap_connector


def delete_expired_sessions():
    """Delete expired sessions.

    Needs an app context to access current_app,
    make sure to create one if necessary.

    E.g.
    >>> with app.app_context():
    >>>     delete_expired_sessions()
    """
    timeout = current_app.config['SESSION_TIMEOUT']

    db = current_app.data.driver.session

    query = db.query(Session).filter(
        Session._updated <= datetime.utcnow() - timeout)

    for entry in query:
        db.delete(entry)

    db.commit()


def run():
    """Run cron tasks.

    Needs an request context for ldap to post/patch items internally,
    make sure to create one if necessary using test_request_context().
    (This will automatically create the app_context for delete_expired_sessions
    as well)

    E.g.
    >>> with app.test_request_context():
    >>>     run()
    """
    delete_expired_sessions()

    if current_app.config['ENABLE_LDAP']:
        ldap_connector.sync_all()

# Run

if __name__ == '__main__':
    # Get an app and run cron with request context.
    app = create_app()

    with app.test_request_context():
        run()
