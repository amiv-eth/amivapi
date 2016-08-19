# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for methods added to '_links'.

Restructure: Test link generation and link adding separate

To understand the test, understand what needs to be tested

Note on link setup. The links in eve are a little inconsistent
- self links only
- GET: self, parent, collection
"""

from copy import deepcopy
import json

from flask import Response

from amivapi.auth.link_methods import (
    _add_methods_to_item_links,
    _add_methods_to_resource_links,
    add_permitted_methods_after_update,
    add_permitted_methods_after_insert,
    add_permitted_methods_after_fetch_item,
    add_permitted_methods_after_fetch_resource,
    add_permitted_methods_for_home
)
from .fake_auth import FakeAuthTest


class LinkTest(FakeAuthTest):
    """Tests for links to permitted methods."""

    # Lists to compare allowed link methods

    home_methods = ['GET', 'HEAD', 'OPTIONS']
    public_resource_methods = ['GET', 'HEAD', 'OPTIONS', 'POST']
    admin_resource_methods = ['GET', 'HEAD', 'OPTIONS', 'POST', 'DELETE']
    public_item_methods = ['GET', 'HEAD', 'OPTIONS', 'PATCH']
    admin_item_methods = ['GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE']

    # Assert all possible item links get correct methods in every context

    def assertItemMethods(self, methods_self, methods_collection,
                          **context):
        """Init context, add methods and compare all required results.

        First test the variant that only a self link exists (POST, PATCH)
        Then the variant with self, collection and parent links (GET)

        Use a default item with id 'item_id'.
        Home endpoint methods are always the same. (Only read.)
        """
        with self._init_context(**context):
            # Set up data to test only self link
            data_self = {
                '_id': 'item_id',
                '_links': {'self': {}}
            }

            # Call and assert results
            _add_methods_to_item_links('fake', data_self)

            self.assertItemsEqual(data_self['_links']['self']['methods'],
                                  methods_self)

            # Set up data to test all limks
            data_all = {
                '_id': 'item_id',
                '_links': {'self': {},
                           'parent': {},
                           'collection': {}}
            }

            # Call and assert results
            _add_methods_to_item_links('fake', data_all)

            self.assertItemsEqual(data_all['_links']['self']['methods'],
                                  methods_self)
            self.assertItemsEqual(data_all['_links']['collection']['methods'],
                                  methods_collection)
            self.assertItemsEqual(data_all['_links']['parent']['methods'],
                                  self.home_methods)

    def test_item_methods_public(self):
        """Read and public methods.

        Public users, registered users without special permissions and admins
        with read only access will all receive the same results.
        """
        for context in [{},
                        {'current_user': 'nothing_special'},
                        {'resource_admin_readonly': True}]:
            self.assertItemMethods(self.public_item_methods,
                                   self.public_resource_methods,
                                   **context)

    def test_item_methods_user_with_access(self):
        """All methods for item, read and public for rest."""
        user = 'item_id'
        self.assertItemMethods(self.admin_item_methods,
                               self.public_resource_methods,
                               current_user=user)

    def test_item_methods_admin(self):
        """All methods."""
        self.assertItemMethods(self.admin_item_methods,
                               self.admin_resource_methods,
                               resource_admin=True)

    # Assert all possible resource links get correct methods in every context

    def assertResourceMethods(self, resource_methods, **context):
        """Assert the resource methods are correct given a certain context.

        Test all pagination possibilities.
        Pagination links have always the same methods as self.

        Home methods are always the same.
        """
        with self._init_context(**context):
            no_pagination = {
                '_links': {'self': {},
                           'parent': {}}
            }

            _add_methods_to_resource_links('fake', no_pagination)

            self.assertItemsEqual(no_pagination['_links']['self']['methods'],
                                  resource_methods)
            self.assertItemsEqual(no_pagination['_links']['parent']['methods'],
                                  self.home_methods)

            with_pagination = {
                '_links': {'self': {},
                           'parent': {},
                           'prev': {},
                           'next': {},
                           'last': {}}
            }

            _add_methods_to_resource_links('fake', with_pagination)

            for link in 'self', 'prev', 'next', 'last':
                self.assertItemsEqual(
                    with_pagination['_links'][link]['methods'],
                    resource_methods)
            self.assertItemsEqual(
                with_pagination['_links']['parent']['methods'],
                self.home_methods)

    def test_resource_methods_public(self):
        """Public methods.

        For both unregistered and registered users as well as read only admins.
        """
        for context in [{},
                        {'current_user': 'item_id'},
                        {'resource_admin_readonly': True}]:
            self.assertResourceMethods(self.public_resource_methods, **context)

    def test_resource_methods_admin(self):
        """All methods."""
        self.assertResourceMethods(self.admin_resource_methods,
                                   resource_admin=True)

    # Assert hooks process data correctly for AmivTokenAuth subclasses.

    def assertMethodsAdded(self, data):
        """Assert that every entry in '_links' has a 'methods' section."""
        for data in data['_links'].values():
            self.assertIn('methods', data)

    def test_add_permitted_methods_after_read_item(self):
        """Test read item for all different auth options."""
        data_template = {
            '_id': 'somethingsomething',
            '_links': {
                'self': {},
                'collection': {},
                'parent': {}}
        }

        data = deepcopy(data_template)

        with self.app.app_context():
            # Nothing if not AmivTokenAuth
            for res in ['fake_nothing', 'fake_no_amiv']:
                add_permitted_methods_after_fetch_item(res, data)
                self.assertEqual(data, data_template)

            add_permitted_methods_after_fetch_item('fake', data)
            self.assertMethodsAdded(data)

    def test_add_permitted_methods_after_read_resource(self):
        """Test read resource for all different auth options."""
        data_template = {
            '_items': [
                {'_id': 'A', '_links': {'self': {}}},
                {'_id': 'B', '_links': {'self': {}}}
            ],
            '_links': {'self': {},
                       'parent': {}}
        }

        data = deepcopy(data_template)

        with self.app.app_context():
            # Nothing if not AmivTokenAuth
            for res in ['fake_nothing', 'fake_no_amiv']:
                add_permitted_methods_after_fetch_resource(res, data)
                self.assertEqual(data, data_template)

            add_permitted_methods_after_fetch_resource('fake', data)

            self.assertMethodsAdded(data)
            for item in data['_items']:
                self.assertMethodsAdded(item)

    def test_add_permitted_methods_after_update(self):
        """Test update hook."""
        data_template = {
            '_id': 'something',
            '_links': {
                'self': {},
            }
        }

        data = deepcopy(data_template)

        with self.app.app_context():
            # Nothing without amiv auth
            for res in ['fake_nothing', 'fake_no_amiv']:
                add_permitted_methods_after_update(res, data)
                self.assertEqual(data, data_template)

            add_permitted_methods_after_update('fake', data)
            self.assertMethodsAdded(data)

    def test_add_permitted_methods_after_insert(self):
        """Test insert.

        It actually doesnt matter if its single or batch insert.
        The hook always receives a list of items.
        """
        data_template = [
            {'_id': 'first', '_links': {'self': {}}},
            {'_id': 'second', '_links': {'self': {}}}
        ]

        data = deepcopy(data_template)

        with self.app.app_context():
            # Nothing without amiv auth
            for res in ['fake_nothing', 'fake_no_amiv']:
                add_permitted_methods_after_insert(res, data)
                self.assertEqual(data, data_template)

            add_permitted_methods_after_insert('fake', data)
            for item in data:
                self.assertMethodsAdded(item)

    # Test home endpoint links

    def test_link_methods_read_home(self):
        """Check link methods for home endpoint.

        We have no dedicated hook here, instead a generic post GET hook will
        parse and modify the flask response.
        """
        # Prepare fake response
        response_data = json.dumps({'_links': {'child': [
            {'title': "fake"},
            {'title': "fake_no_amiv"},
            {'title': "fake_nothing"},
        ]}})

        # test = (context_variables, expected_test_methods)
        for test in [({}, self.public_resource_methods),
                     ({'resource_admin': True}, self.admin_resource_methods)]:
            with self._init_context(**test[0]):
                response = Response(response_data)
                add_permitted_methods_for_home(None, None, response)

                modified_data = response.get_data().decode('utf-8')
                modified_links = json.loads(modified_data)['_links']['child']

                self.assertItemsEqual(modified_links[0]['methods'], test[1])

                # Nothing for not AmivAuth
                self.assertNotIn('methods', modified_links[1])
                self.assertNotIn('methods', modified_links[2])
