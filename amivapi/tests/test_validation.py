# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test general purpose validators."""

import json
from bson import ObjectId

from amivapi.tests.utils import WebTest


class ValidatorAMIVTest(WebTest):
    """Unit test class for general purpose validators."""

    def test_session_younger_than_s(self):
        """Test the session_younger_than_s validator."""

        # TODO implement test
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'string',
                    'session_younger_than_s': 60
                }
            }
        })

        self.api.post("/test", data={
            'field1': 'teststring'
        }, status_code=201)

        self.api.post("/test", data={
            'field1': 'teststring',
        }, status_code=422)

    def get_user_token(self, user_id, created):
        """Create session for a user and return a token.

        Args:
            user_id (str): user_id as string.

        Returns:
            str: Token that can be used to authenticate user.
        """
        token = "test_token_" + str(next(self.counter))
        self.db['sessions'].insert({u'user': ObjectId(user_id),
                                    u'token': token})
        return token