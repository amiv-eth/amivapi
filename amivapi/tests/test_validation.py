# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test general purpose validators."""

from datetime import datetime, timedelta, timezone

from amivapi.auth.auth import AmivTokenAuth
from amivapi.tests.utils import WebTest


class ValidatorAMIVTest(WebTest):
    """Unit test class for general purpose validators."""

    def test_session_younger_than(self):
        """Test the session_younger_than validator."""
        user = self.new_object("users")

        token = self.get_user_token(user['_id'])
        old_token = self.get_user_token(
            user['_id'],
            created=datetime.now(timezone.utc) - timedelta(minutes=2))

        class AllowEverythingAuth(AmivTokenAuth):
            def has_resource_write_permission(*_):
                return True

            def has_item_write_permission(*_):
                return True

        self.app.register_resource('test', {
            'authentication': AllowEverythingAuth,

            'schema': {
                'field1': {
                    'type': 'string',
                    'session_younger_than': timedelta(minutes=1)
                }
            }
        })

        # Outdated token may not post
        self.api.post("/test", data={
            'field1': 'teststring'
        }, token=old_token, status_code=422)

        # New token can post
        self.api.post("/test", data={
            'field1': 'teststring',
        }, token=token, status_code=201)

        admin_group = self.new_object("groups",
                                      permissions={'test': 'readwrite'})
        self.new_object("groupmemberships",
                        user=user['_id'], group=admin_group['_id'])

        # User is now admin, so can always post
        self.api.post("/test", data={
            'field1': 'teststring2'
        }, token=old_token, status_code=201)
