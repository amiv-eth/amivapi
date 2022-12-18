# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test general purpose validators."""

from datetime import datetime, timedelta, timezone

from amivapi.auth.auth import AmivTokenAuth
from amivapi.tests.utils import WebTest, WebTestNoAuth
from amivapi.validation import ValidatorAMIV

class ValidatorAMIVTestNoAuth(WebTestNoAuth):
    """Unit test class for general purpose validators w/o authentication."""

    def test_validate_no_html(self):
        """Test no-html validator."""
        self.app.register_resource('test', {
            'schema': {
                'field': {
                    'type': 'string',
                    'no_html': True
                }
            }
        })

        has_html = '<head><title>I\'m title</title></head>Hello, <b>world</b>'
        has_no_html = 'ich <3 du und="test" d:> ichht fldf d<'

        self.api.post('/test', data={
            'field': has_html
        }, status_code=422)

        self.api.post('/test', data={
            'field': has_no_html
        }, status_code=201)

    def test_validate_url(self):
        """Test url validator."""
        self.app.register_resource('test', {
            'schema': {
                'field': {
                    'type': 'string',
                    'url': True
                }
            }
        })

        valid_urls = [
            'http://amiv.ethz.ch/test',
            'https://amiv.ethz.ch/test',
            'https://amiv.ethz.ch/',
            'http://amiv.ethz.ch/test#testAnchor'
            'http://amiv.ethz.ch/test?param=yes'
        ]
        invalid_urls = [
            'amiviscool',
            'www.amiv.ethz.ch',
            'www.amiv.ethz.ch/test',
            'ftp://example.amiv.ethz.ch/'
        ]

        for valid_url in valid_urls:
            print(valid_url)
            self.api.post('/test', data={
                'field': valid_url
            }, status_code=201)

        for invalid_url in invalid_urls:
            self.api.post('/test', data={
                'field': invalid_url
            }, status_code=422)


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

    def _assert_post_valid(self, validator, document):
        with self.app.test_request_context(method='POST'):
            self.assertTrue(validator.validate(document=document))

    def _assert_post_invalid(self, validator, document):
        with self.app.test_request_context(method='POST'):
            self.assertFalse(validator.validate(document=document))

    def _assert_patch_valid(self, validator, updates, original):
        with self.app.test_request_context(method='PATCH'):
            self.assertTrue(validator.validate_update(
                document=updates,
                document_id=None,
                persisted_document=original))

    def _assert_patch_invalid(self, validator, updates, original):
        with self.app.test_request_context(method='PATCH'):
            self.assertFalse(validator.validate_update(
                document=updates,
                document_id=None,
                persisted_document=original))

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
