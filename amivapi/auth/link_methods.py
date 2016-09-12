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

from .auth import AmivTokenAuth, authenticate


def _get_item_methods(resource, item):
    is_admin = g.get('resource_admin')
    user = g.get('current_user')  # TODO: post_internal_problem
    res = current_app.config['DOMAIN'][resource]
    auth = resource_auth(resource)

    # If the item is displayed, the read methods are obviously allowed
    methods = ['GET', 'HEAD', 'OPTIONS'] + res['public_item_methods']

    # Admins have access to all methods. For non admins check user permission.
    if is_admin or auth.has_write_permission(user, item):
        methods += res['item_methods']

    # Remove duplicates before returning
    return list(set(methods))


def _get_resource_methods(resource):
    res = current_app.config['DOMAIN'][resource]

    # public methods and OPTIONS are always available
    methods = res['public_methods'] + ['OPTIONS']
    if 'GET' in methods:
        methods += ['HEAD']

    # Unless for items, resources may not have public read access
    if (g.get('current_user') or
            g.get('resource_admin_readonly') or
            g.get('resource_admin')):
        methods += ['GET', 'HEAD']

    # non public write methods only for resource admins
    if g.get('resource_admin'):
        methods += res['resource_methods']

    # Remove duplicates
    return list(set(methods))


def _home_link_methods():
    return ['GET', 'HEAD', 'OPTIONS']


def add_methods_to_item_links(resource, item):
    """Add methods to all links of the item.

    Args:
        resource (str): The name of the resource
        item (dict): The item, must have a 'links' key.
    """
    links = item['_links']

    # self
    links['self']['methods'] = _get_item_methods(resource, item)

    # parent, i.e. home -> only read methods (optional)
    if 'parent' in links:
        links['parent']['methods'] = _home_link_methods()

    # collection -> resource (optional)
    if 'collection' in links:
        links['collection']['methods'] = _get_resource_methods(resource)


def add_methods_to_resource_links(resource, response):
    """Add methods to all links of the item.

    Args:
        resource (str): The name of the resource
        response (dict): A dict containing the response. Must have the key
            'links'.
    """
    links = response['_links']

    # 'parent' (home)
    links['parent']['methods'] = _home_link_methods()

    # Same links for self and all pagination links
    res_links = _get_resource_methods(resource)
    for link in 'self', 'prev', 'next', 'last':
        if link in links:
            links[link]['methods'] = res_links


def add_permitted_methods_after_insert(resource, items):
    """Need the same links as update, but input is a list of items."""
    if isinstance(resource_auth(resource), AmivTokenAuth):
        for item in items:
            add_methods_to_item_links(resource, item)


def add_permitted_methods_after_fetch_item(resource, item):
    """Basically like insert and update, but there is more link info."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        add_methods_to_item_links(resource, item)


def add_permitted_methods_after_fetch_resource(resource, response):
    """Resource links in response and list of items with 'self' links."""
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        print(response)

        # Item links
        for item in response['_items']:
            add_methods_to_item_links(resource, item)

        # Resource links
        add_methods_to_resource_links(resource, response)


def _get_data(response):
    """Get response data as dict.

    Encoding/Decoding necessary for compatibility with python 2 and 3.
    """
    return json.loads(response.get_data().decode('utf-8'))


def _set_data(response, data):
    """Jsonify dict and set as response data."""
    response.set_data(json.dumps(data))


def add_permitted_methods_after_update(resource, request, response):
    """Add permitted methods to "_links" part of item.

    This needs to be used as a `on_post_PATCH` hook, since the update hooks
    do not contain the links (unline fetch and insert)
    """
    # Only continue for AmivTokenAuth subclass
    if isinstance(resource_auth(resource), AmivTokenAuth):
        item_data = _get_data(response)

        add_methods_to_item_links(resource, item_data)

        _set_data(response, item_data)


def add_permitted_methods_for_home(resource, request, response):
    """Add methods for GET to "/".

    This one is special. We can only get this request with the general GET
    hook, which Eve will call with `resource=None` for the home endpoint.
    """
    if resource is None:
        # The home endpoint has no hooks before it. We need to call
        # authentication manually
        authenticate()

        # Retrieve data (json as string) for request and parse
        # Decode to be compatible with python 2 (str) and 3 (binary)
        data = _get_data(response)

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
            _set_data(response, data)
