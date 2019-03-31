# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test general purpose validators."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from eve.io.mongo import Validator as Validator

from amivapi.auth.auth import AmivTokenAuth
from amivapi.tests.utils import WebTest
from amivapi.validation import ValidatorAMIV


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

    def _assert_post_valid(self,
                           v: Validator,
                           doc: Dict[str, Any]) -> None:
        with self.app.test_request_context(method='POST'):
            self.assertTrue(v.validate(document=doc))

    def _assert_post_invalid(self,
                             v: Validator,
                             doc: Dict[str, Any]) -> None:
        with self.app.test_request_context(method='POST'):
            self.assertFalse(v.validate(document=doc))

    def _assert_patch_valid(self,
                            v: Validator,
                            update: Dict[str, Any],
                            orig: Dict[str, Any]) -> None:
        with self.app.test_request_context(method='PATCH'):
            self.assertTrue(v.validate_update(
                document=update, document_id=None, persisted_document=orig))

    def _assert_patch_invalid(self,
                              v: Validator,
                              update: Dict[str, Any],
                              orig: Dict[str, Any]) -> None:
        with self.app.test_request_context(method='PATCH'):
            self.assertFalse(v.validate_update(
                document=update, document_id=None, persisted_document=orig))

    def test_dependencies(self):
        """Test the dependencies validator."""
        schema = {
            'field1': {
                'type': 'string',
                'dependencies': ['field2', 'field3'],
            },
            'field2': {
                'type': 'string',
            },
            'field3': {
                'type': 'string',
            },
        }
        v = ValidatorAMIV(schema=schema)

        self._assert_post_invalid(v, {'field1': 'a'})
        self._assert_post_invalid(v, {'field1': 'a', 'field2': 'a'})
        self._assert_post_invalid(
            v, {'field1': 'a', 'field2': 'a', 'field3': None})
        self._assert_post_valid(v, {'field1': None})
        self._assert_post_valid(v,
                                {'field1': 'a', 'field2': 'a', 'field3': 'a'})

        # Test patching other field.
        self._assert_patch_valid(v, {'field3': 'a'}, {})
        self._assert_patch_valid(v, {'field3': 'b'},
                                 {'field1': 'a', 'field2': 'a', 'field3': 'a'})

        # Test adding field.
        self._assert_patch_invalid(v, {'field1': 'a'}, {})
        self._assert_patch_invalid(v, {'field1': 'a'},
                                   {'field2': None, 'field3': 'a'})
        self._assert_patch_invalid(v, {'field1': 'a'}, {'field2': 'a'})
        self._assert_patch_valid(v, {'field1': 'a'},
                                 {'field2': 'a', 'field3': 'a'})
        self._assert_patch_valid(v, {'field1': 'a', 'field2': 'a'},
                                 {'field3': 'a'})

        # Test deleting field.
        doc_with_all_set = {'field1': 'a', 'field2': 'a', 'field3': 'a'}
        self._assert_patch_invalid(v, {'field2': None}, doc_with_all_set)
        self._assert_patch_valid(v, {'field1': None, 'field2': None},
                                 doc_with_all_set)
        self._assert_patch_valid(v, {'field1': None}, doc_with_all_set)
