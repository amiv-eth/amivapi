# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Functions adding permitted methods to '_links' part of response.

TODO: Multiple pages!
"""


import json

from flask import current_app, g

from eve.auth import resource_auth

from .auth import AmivTokenAuth

READ_METHODS = ['GET', 'HEAD', 'OPTIONS']


def _item_link_methods(resource, item):
    is_admin = g.get('resource_admin')
    user = g.get('current_user')  # TODO: post_internal_problem
    res = current_app.config['DOMAIN'][resource]
    auth = resource_auth(resource)

    methods = READ_METHODS + res['public_item_methods']

    # Admins have access to all methods. Otherwise check per item.
    if is_admin or (user and auth.has_write_permission(user, item)):
        methods += res['item_methods']

    # Remove duplicates before returning
    return list(set(methods))


def _resource_link_methods(resource):
    res = current_app.config['DOMAIN'][resource]

    # all returned items are readable. public methods always available
    methods = READ_METHODS + res['public_methods']

    # non public methods only for resource admins
    if g.get('resource_admin'):
        methods += res['resource_methods']

    # Remove duplicates
    return list(set(methods))


def _home_link_methods():
    return READ_METHODS


def add_permitted_methods_after_update(resource, item):
    """Add permitted methods to "_links" part of item."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        # Eve only includes link to 'self'
        item['_links']['self']['methods'] = _item_link_methods(resource, item)


def add_permitted_methods_after_insert(resource, items):
    """Need the same links as update, but input is a list of items."""
    if isinstance(resource_auth(resource), AmivTokenAuth):
        for item in items:
            item['_links']['self']['methods'] = \
                _item_link_methods(resource, item)


def add_permitted_methods_after_fetch_item(resource, item):
    """Basically like insert and update, but there is more link info."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        links = item['_links']
        # self
        links['self']['methods'] = _item_link_methods(resource, item)

        # parent, i.e. home -> only read methods
        links['parent']['methods'] = _home_link_methods()

        # collection -> resource
        links['collection']['methods'] = _resource_link_methods(resource)


def add_permitted_methods_after_fetch_resource(resource, response):
    """Resource links in response and list of items with 'self' links."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        # Item links
        for item in response['_items']:
            item['_links']['self']['methods'] = \
                _item_link_methods(resource, item)

        # Resource links
        links = response['_links']
        # 'parent' (home)
        links['parent']['methods'] = _home_link_methods()
        # 'self', the collection
        links['self']['methods'] = _resource_link_methods(resource)


def add_permitted_methods_for_home(resource, request, response):
    """Add methods for GET to "/".

    This one is special. We can only get this request with the general GET
    hook, which Eve will call with `resource=None` for the home endpoint.
    """
    if resource is None:
        # Retrieve data (json as string) for request and parse
        data = json.loads(response.get_data())

        try:
            for res_link in data['_links']['child']:
                res_name = res_link['title']  # title equals resource
                # Only AmivAuth
                if isinstance(resource_auth(res_name), AmivTokenAuth):
                    res_link['methods'] = _resource_link_methods(res_name)
        except KeyError:
            # Other endpoints like `schemaendpoint` might end u here, but don't
            # have the same 'link' layout as home, so we can just ignore them
            pass

        # Overwrite response data with modified version
        response.set_data(json.dumps(data))
