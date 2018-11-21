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

from flask import g, Response

from amivapi.auth.link_methods import (
    add_methods_to_item_links,
    add_methods_to_resource_links,
    add_permitted_methods_after_fetch_item,
    add_permitted_methods_after_fetch_resource,
    add_permitted_methods_after_insert,
    add_permitted_methods_after_update,
    add_permitted_methods_for_home
)
from amivapi.tests.auth.fake_auth import FakeAuthTest
from amivapi.tests.utils import WebTest


def get_response_data(response):
    """Helper to check data of response object."""
    return json.loads(response.get_data(as_text=True))


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
            add_methods_to_item_links('fake', data_self)

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
            add_methods_to_item_links('fake', data_all)

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

            add_methods_to_resource_links('fake', no_pagination)

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

            add_methods_to_resource_links('fake', with_pagination)

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

    def test_resource_methods_user_withaccess(self):
        """All methods for user with name 'allowed' - see fake auth."""
        self.assertResourceMethods(self.admin_resource_methods,
                                   current_user='allowed')

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

    def test_add_permitted_methods_after_update(self):
        """Test update hook."""
        data = {
            '_id': 'something',
            '_links': {
                'self': {},
            }
        }

        response = Response(json.dumps(data))

        with self.app.app_context():
            # Nothing without amiv auth
            for resource in ['fake_nothing', 'fake_no_amiv']:
                add_permitted_methods_after_update(resource, None, response)
                response_data = get_response_data(response)
                self.assertEqual(response_data, data)

            add_permitted_methods_after_update('fake', None, response)
            response_data = get_response_data(response)
            self.assertMethodsAdded(response_data)

    def test_no_methods_after_patch_error(self):
        """Test that no methods are added for errors."""
        data = "somethingsomething error"
        response = Response(data)
        response.status_code = 400

        add_permitted_methods_after_update('fale', None, response)
        self.assertEqual(data, response.get_data().decode('utf-8'))

    # Test home endpoint links

    def test_link_methods_read_home(self):
        """Check link methods for home endpoint.

        We have no dedicated hook here, instead a generic post GET hook will
        parse and modify the flask response.
        """
        # Copy the fake resource so we can use the second one as admin resource
        self.app.config['DOMAIN']['fake_2'] = self.app.config['DOMAIN']['fake']

        # Prepare fake response
        response_data = {'_links': {'child': [
            {'href': "fake"},
            {'href': "fake_2"},
            {'href': "fake_no_amiv"},
            {'href': "fake_nothing"},
        ]}}

        response = Response(json.dumps(response_data))

        # Add a hook that set resource admin for second resource
        # In reality a group or something would do this.
        def admin_hook(resource):
            if resource == "fake_2":
                g.resource_admin = True

        self.app.after_auth += admin_hook

        with self.app.test_request_context():
            add_permitted_methods_for_home(None, None, response)

            links = get_response_data(response)['_links']['child']

            # No admin, public methods
            self.assertItemsEqual(links[0]['methods'],
                                  self.public_resource_methods)

            # Admin
            self.assertItemsEqual(links[1]['methods'],
                                  self.admin_resource_methods)

            # Nothing if not AmivAuth (second and third element in list)
            self.assertNotIn('methods', links[2])
            self.assertNotIn('methods', links[3])


class LinkIntegrationTest(WebTest):
    """Test if everything works well with Eve.

    Not using any fake auth classes here, we will just look at the users
    resource and home endpoint to check the results.
    """

    def setUp(self):
        """Create two test users on setup."""
        super().setUp()

        self.user = self.new_object('users', membership='regular')
        self.other_user = self.new_object('users', membership='regular')

        self.user_id = str(self.user['_id'])
        self.other_user_id = str(self.other_user['_id'])

        self.user_token = self.get_user_token(str(self.user['_id']))
        self.root_token = self.get_root_token()

    def get_user_methods(self, response):
        """Helper to filter GET to home to get methods for user res."""
        for links in response.json['_links']['child']:
            if links['href'] == 'users':
                return links['methods']

    def test_home_public(self):
        """Test GET on home for public user."""
        response = self.api.get("/", status_code=200)
        self.assertItemsEqual(self.get_user_methods(response),
                              ['OPTIONS'])

    def test_home_registered(self):
        """Test GET on home for a registered user."""
        response = self.api.get("/", token=self.user_token, status_code=200)
        self.assertItemsEqual(self.get_user_methods(response),
                              ['OPTIONS', 'GET', 'HEAD'])

    def test_home_admin(self):
        """Test GET on home for an admin."""
        response = self.api.get("/", token=self.root_token, status_code=200)
        self.assertItemsEqual(self.get_user_methods(response),
                              ['OPTIONS', 'GET', 'HEAD', 'POST'])

    def test_resource_registered(self):
        """Test GET on resource for a registered user."""
        response = self.api.get("/users",
                                token=self.user_token,
                                status_code=200).json

        # Parent = /, self = /users
        for link in 'parent', 'self':
            methods = response['_links'][link]['methods']
            self.assertItemsEqual(methods, ['GET', 'HEAD', 'OPTIONS'])

        for item in response['_items']:
            # Only self
            methods = item['_links']['self']['methods']

            if item['_id'] == self.user_id:
                self.assertItemsEqual(methods, ['GET', 'HEAD', 'OPTIONS',
                                                'PATCH', 'DELETE'])
            else:
                self.assertItemsEqual(methods, ['GET', 'HEAD', 'OPTIONS'])

    def test_resource_admin(self):
        """Test GET on resource for a registered user."""
        response = self.api.get("/users",
                                token=self.root_token,
                                status_code=200).json

        home_methods = response['_links']['parent']['methods']
        self.assertItemsEqual(home_methods, ['GET', 'HEAD', 'OPTIONS'])

        resource_methods = response['_links']['self']['methods']
        self.assertItemsEqual(resource_methods,
                              ['GET', 'HEAD', 'OPTIONS', 'POST'])

        for item in response['_items']:
            # Only self
            methods = item['_links']['self']['methods']
            self.assertItemsEqual(methods, ['GET', 'HEAD', 'OPTIONS',
                                            'PATCH', 'DELETE'])

    def _get_methods(self, response, link):
        return response.json['_links'][link]['methods']

    def test_item_registered_privileged(self):
        """Test GET on item for user with permissions."""
        response = self.api.get("/users/" + self.user_id,
                                token=self.user_token,
                                status_code=200)

        # Home = parent
        self.assertItemsEqual(self._get_methods(response, 'parent'),
                              ['GET', 'HEAD', 'OPTIONS'])
        # Resource = collection
        self.assertItemsEqual(self._get_methods(response, 'collection'),
                              ['GET', 'HEAD', 'OPTIONS'])

        # Item = self
        self.assertItemsEqual(self._get_methods(response, 'self'),
                              ['GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'])

    def test_item_registered_unprivileged(self):
        """Test GET on item for user with permissions."""
        response = self.api.get("/users/" + self.other_user_id,
                                token=self.user_token,
                                status_code=200)

        # Home = parent
        self.assertItemsEqual(self._get_methods(response, 'parent'),
                              ['GET', 'HEAD', 'OPTIONS'])
        # Resource = collection
        self.assertItemsEqual(self._get_methods(response, 'collection'),
                              ['GET', 'HEAD', 'OPTIONS'])

        # Item = self
        self.assertItemsEqual(self._get_methods(response, 'self'),
                              ['GET', 'HEAD', 'OPTIONS'])

    def test_item_admin(self):
        """Test GET on item for user with permissions."""
        response = self.api.get("/users/" + self.other_user_id,
                                token=self.root_token,
                                status_code=200)

        # Home = parent
        self.assertItemsEqual(self._get_methods(response, 'parent'),
                              ['GET', 'HEAD', 'OPTIONS'])
        # Resource = collection
        self.assertItemsEqual(self._get_methods(response, 'collection'),
                              ['GET', 'HEAD', 'OPTIONS', 'POST'])

        # Item = self
        self.assertItemsEqual(self._get_methods(response, 'self'),
                              ['GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'])

    def test_post(self):
        """Test POST on users. Only available for admin."""
        data = {
            'firstname': 'Pablo',
            'lastname': 'Pablone',
            'membership': 'regular',
            'email': 'pablo@pablomail.com',
            'gender': 'male',
        }

        response = self.api.post("/users",
                                 data=data,
                                 token=self.root_token,
                                 status_code=201)

        self.assertItemsEqual(self._get_methods(response, 'self'),
                              ['GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'])

    def test_patch(self):
        """Test PATCH by normal user and admin."""
        user = self.new_object('users', email="original@amiv.ch")
        user_id = str(user['_id'])

        updates = {'email': 'new@amiv.ch'}
        headers = {'If-Match': user['_etag']}

        user_response = self.api.patch("/users/" + user_id,
                                       data=updates,
                                       headers=headers,
                                       token=self.get_user_token(user_id),
                                       status_code=200)

        self.assertItemsEqual(self._get_methods(user_response, 'self'),
                              ['GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'])

        updates = {'email': 'new2@amiv.ch'}
        headers = {'If-Match': user_response.json['_etag']}

        admin_response = self.api.patch("/users/" + user_id,
                                        data=updates,
                                        headers=headers,
                                        token=self.root_token,
                                        status_code=200)

        self.assertItemsEqual(self._get_methods(admin_response, 'self'),
                              ['GET', 'HEAD', 'OPTIONS', 'PATCH', 'DELETE'])

    def test_bad_patch(self):
        """Test unsuccessful patch.

        The patch method uses a post_PATCH hook, witch is executed for errors
        as well. No link methods can be added then.
        """
        user = self.new_object('users', email="original@amiv.ch")
        user_id = str(user['_id'])

        bad_updates = {'nethz': "can't be patched"}
        headers = {'If-Match': user['_etag']}

        self.api.patch("/users/" + user_id,
                       data=bad_updates,
                       headers=headers,
                       token=self.get_user_token(user_id),
                       status_code=422)
