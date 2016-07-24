# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for methods added to '_links'."""

import json
from copy import deepcopy

from flask.wrappers import Response

from amivapi.test.util import WebTest
from amivapi.auth import (
    add_permitted_methods_after_update,
    add_permitted_methods_after_insert,
    add_permitted_methods_after_fetch_item,
    add_permitted_methods_after_fetch_resource,
    add_permitted_methods_for_home
)


class FakeAuth(AmivTokenAuth):
    """Testing auth class that makes it easy to check results."""

    def create_user_lookup_filter(self, user_id):
        """Simple lookup."""
        return {'_id': user_id}

    def has_write_permission(self, user_id, item):
        """Return true if _id field equals user."""
        return user_id == item['_id']


class LinkTest(WebTest):
    """Tests for links to permitted methods."""

    # Sets to compare allowed link methods
    home_methods = {'GET', 'HEAD', 'OPTIONS'}
    normal_methods = {'GET', 'HEAD', 'OPTIONS', 'POST'}
    admin_methods = {'GET', 'HEAD', 'OPTIONS', 'POST', 'DELETE'}
    normal_item_methods = {'GET', 'HEAD', 'OPTIONS', 'PATCH'}
    admin_item_methods = {'GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'}

    def setUp(self):
        """Setup with fake resources that have only auth.

        - AmivTokenAuth subclass for the resource 'fake'.
        - A 'BasicAuth' (from Eve) subclass for 'fake_no_amiv'
        - No auth at all for 'fake_nothing'

        """
        super(LinkTest, self).setUp()

        self.app.config['DOMAIN']['fake'] = {
            'authentication': FakeAuth,
            # some different methods for public and not public
            'resource_methods': ['GET', 'POST', 'DELETE'],
            'public_methods': ['GET', 'POST'],
            'item_methods': ['GET', 'PATCH', 'DELETE'],
            'public_item_methods': ['GET', 'PATCH']
        }

    def test_link_methods_read_home(self):
        """Check link methods for home endpoint."""
        response_data = json.dumps({'_links': {'child': [
            {'title': "fake"},
            {'title': "fake_no_amiv"},
            {'title': "fake_nothing"},
        ]}})

        # use tuple (context_variables, expected_test_methods)
        for test in [({}, self.normal_methods),
                     ({'resource_admin': True}, self.admin_methods)]:
            with self._init_context(**test[0]):
                response = Response(response_data)
                add_permitted_methods_for_home(None, None, response)

                modified_data = response.get_data()
                modified_links = json.loads(modified_data)['_links']['child']

                self.assertEqual(set(modified_links[0]['methods']), test[1])

                # Nothing for not AmivAuth
                self.assertNotIn('methods', modified_links[1])
                self.assertNotIn('methods', modified_links[2])

    def test_link_methods_read_resource(self):
        """Test link methods for GET to resource.

        Only resource admin can use all methods, not readonly admin.
        """
        data_template = {'_items': [{'_links': {'self': {}}}],
                         '_links': {'self': {},
                                    'parent': {}}}

        # Nothing for different auth
        with self._init_context():
            for res in 'fake_no_amiv', 'fake_nothing':
                data = deepcopy(data_template)
                add_permitted_methods_after_fetch_resource(res, data)
                self.assertEqual(data, data_template)

        # Now AmivTokenAuth subclass
        # tuple (context_var, expected_resource_methods)
        for test in [
                ({}, self.normal_methods),
                ({'resource_admin_readonly': True}, self.normal_methods),
                ({'resource_admin': True}, self.admin_methods)]:
            with self._init_context(**test[0]):
                data = deepcopy(data_template)
                add_permitted_methods_after_fetch_resource('fake', data)

                links = data['_links']
                self.assertEqual(self.home_methods,
                                 set(links['parent']['methods']))
                self.assertEqual(test[1], set(links['self']['methods']))

    def test_item_link_methods_read_resource(self):
        """Test that all items have their permissions handled indiidually."""
        user_id = 'abcd123'

        data_template = {
            '_items': [
                {'_id': user_id, '_links': {'self': {}}},
                {'_id': 'notuser', '_links': {'self': {}}}
            ],
            '_links': {'self': {},
                       'parent': {}}
        }

        def _assert_combination(items, all_methods):
            """Match allowed methods with items."""
            for (item, methods) in zip(items, all_methods):
                self.assertEqual(set(item['_links']['self']['methods']),
                                 methods)

        # User has all methods for item 0 only
        # tupel (context_vars, list of permissions for each item)
        for test in [
                ({'resource_admin_readonly': True},
                 [self.normal_item_methods] * 2),
                ({'resource_admin': True},
                 [self.admin_item_methods] * 2),
                ({'current_user': user_id},
                 [self.admin_item_methods, self.normal_item_methods])]:
            with self._init_context(**test[0]):
                data = deepcopy(data_template)
                add_permitted_methods_after_fetch_resource('fake', data)
                _assert_combination(
                    data['_items'],
                    test[1])

    def test_link_methods_read_item(self):
        """Test link methods for GET to item."""
        user_id = "someid"

        data_template = {
            '_id': user_id,  # fake_auth grants permission if _id equals user
            '_links': {
                'self': {},
                'collection': {},
                'parent': {}}
        }

        # Nothing if not amivauth
        with self._init_context():
            for res in 'fake_no_amiv', 'fake_nothing':
                data = deepcopy(data_template)
                add_permitted_methods_after_fetch_item(res, data)
                self.assertEqual(data, data_template)

        # tuple (context_var, expected_resource_methods, expected_item_methods)
        for test in [({},
                      self.normal_methods, self.normal_item_methods),
                     ({'resource_admin_readonly': True},
                      self.normal_methods, self.normal_item_methods),
                     ({'resource_admin': True},
                      self.admin_methods, self.admin_item_methods),
                     ({'current_user': user_id},
                      self.normal_methods, self.admin_item_methods)]:
            with self._init_context(**test[0]):
                data = deepcopy(data_template)
                add_permitted_methods_after_fetch_item('fake', data)

                # self
                self.assertEqual(set(data['_links']['self']['methods']),
                                 test[2])

                # collection
                self.assertEqual(set(data['_links']['collection']['methods']),
                                 test[1])

                # parent
                self.assertEqual(set(data['_links']['parent']['methods']),
                                 self.home_methods)

    def test_link_methods_insert(self):
        """Test link methods for insert and update. Only "self" links here."""
        user_id = "someid"

        data_template = {
            '_id': user_id,  # fake_auth grants permission if _id equals user
            '_links': {
                'self': {},
            }
        }

        # Nothing if not amivauth
        with self._init_context():
            for res in 'fake_no_amiv', 'fake_nothing':
                data = deepcopy(data_template)
                add_permitted_methods_after_fetch_item(res, data)
                self.assertEqual(data, data_template)

        # tuple (context_var, expected_item_methods)
        for test in [({},
                      self.normal_item_methods),
                     ({'resource_admin_readonly': True},
                      self.normal_item_methods),
                     ({'resource_admin': True},
                      self.admin_item_methods),
                     ({'current_user': user_id},
                      self.admin_item_methods)]:
            with self._init_context(**test[0]):
                data = deepcopy(data_template)
                add_permitted_methods_after_insert('fake', data)

                # self
                self.assertEqual(set(data['_links']['self']['methods']),
                                 test[2])
