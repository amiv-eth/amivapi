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

# Low level: Get methods

READ_METHODS = ['GET', 'HEAD', 'OPTIONS']


def _get_item_methods(resource, item):
    is_admin = g.get('resource_admin')
    user = g.get('current_user')  # TODO: post_internal_problem
    res = current_app.config['DOMAIN'][resource]
    auth = resource_auth(resource)

    methods = READ_METHODS + res['public_item_methods']

    # Admins have access to all methods. Otherwise check per item.
    if is_admin or auth.has_write_permission(user, item):
        methods += res['item_methods']

    # Remove duplicates before returning
    return list(set(methods))


def _get_resource_methods(resource):
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


def _add_methods_to_item_links(resource, item):
    links = item['_links']

    # self
    links['self']['methods'] = _get_item_methods(resource, item)

    # parent, i.e. home -> only read methods (optional)
    if 'parent' in links:
        links['parent']['methods'] = _home_link_methods()

    # collection -> resource (optional)
    if 'collection' in links:
        links['collection']['methods'] = _get_resource_methods(resource)


def _add_methods_to_resource_links(resource, response):
    links = response['_links']

    # 'parent' (home)
    links['parent']['methods'] = _home_link_methods()

    # Same links for self and all pagination links
    res_links = _get_resource_methods(resource)
    for link in 'self', 'prev', 'next', 'last':
        if link in links:
            links[link]['methods'] = res_links


def add_permitted_methods_after_update(resource, item):
    """Add permitted methods to "_links" part of item."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        _add_methods_to_item_links(resource, item)


def add_permitted_methods_after_insert(resource, items):
    """Need the same links as update, but input is a list of items."""
    if isinstance(resource_auth(resource), AmivTokenAuth):
        for item in items:
            _add_methods_to_item_links(resource, item)


def add_permitted_methods_after_fetch_item(resource, item):
    """Basically like insert and update, but there is more link info."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        _add_methods_to_item_links(resource, item)


def add_permitted_methods_after_fetch_resource(resource, response):
    """Resource links in response and list of items with 'self' links."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        print(response)

        # Item links
        for item in response['_items']:
            _add_methods_to_item_links(resource, item)

        # Resource links
        _add_methods_to_resource_links(resource, response)


def add_permitted_methods_for_home(resource, request, response):
    """Add methods for GET to "/".

    This one is special. We can only get this request with the general GET
    hook, which Eve will call with `resource=None` for the home endpoint.
    """
    if resource is None:
        # Retrieve data (json as string) for request and parse
        data = json.loads(response.get_data())

        try:
            links = data['_links']['child']
        except KeyError:
            # Other endpoints like `schemaendpoint` might end u here, but don't
            # have the same 'link' layout as home, so we can just ignore them
            pass
        else:
            # Add links for home
            for res_link in links:
                res_name = res_link['title']  # title equals resource
                # Only AmivAuth
                if isinstance(resource_auth(res_name), AmivTokenAuth):
                    res_link['methods'] = _get_resource_methods(res_name)

            # Overwrite response data with modified version
            response.set_data(json.dumps(data))
