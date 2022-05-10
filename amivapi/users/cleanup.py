# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Delete inactive users to keep the database clean"""

from datetime import timedelta, datetime
from flask import current_app as app

from amivapi.cron import periodic


@periodic(timedelta(days=28))
def remove_inactive_users():
    """Delete non-amiv-members, which were not active for more than one year"""
    dueDate = datetime.now() - timedelta(days=365)

    app.data.driver.db['users'].delete_many(
        {'$and': [{'_updated': {'$lt': dueDate}}, {'membership': 'none'}]})
