# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Functions adding permitted methods to '_links' part of response.

Links are only added for resources using AmivTokenAuth.
"""

import json

from flask import current_app, g
from eve.auth import resource_auth

from .auth import AmivTokenAuth, authenticate, check_if_admin


def _get_item_methods(resource, item):
    res = current_app.config['DOMAIN'][resource]
    user = g.get('current_user')  # TODO: post_internal_problem
    auth = resource_auth(resource)
    is_admin = g.get('resource_admin')

    # If the item is displayed, the read methods are obviously allowed
    methods = ['GET', 'HEAD', 'OPTIONS'] + res['public_item_methods']

    # Admins have access to all methods. For non admins check user permission.
    if is_admin or auth.has_item_write_permission(user, item):
        methods += res['item_methods']

    # Remove duplicates before returning
    return list(set(methods))


def _get_resource_methods(resource):
    res = current_app.config['DOMAIN'][resource]
    auth = resource_auth(resource)
    user = g.get('current_user')
    is_admin = g.get('resource_admin')

    # public methods and OPTIONS are always available
    methods = res['public_methods'] + ['OPTIONS']
    if 'GET' in methods:
        methods += ['HEAD']

    # resources may not have public read access, but we still can see the
    # resource on the home endpoint
    if user or is_admin or g.get('resource_admin_readonly'):
        methods += ['GET', 'HEAD']

    # write methods
    if is_admin or auth.has_resource_write_permission(user):
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
    """Add link methods with an on_inserted hook."""
    if isinstance(resource_auth(resource), AmivTokenAuth):
        for item in items:
            add_methods_to_item_links(resource, item)


def add_permitted_methods_after_fetch_item(resource, item):
    """Add link methods with an on_fetched_item hook."""
    if isinstance(resource_auth(resource), AmivTokenAuth):
        add_methods_to_item_links(resource, item)


def add_permitted_methods_after_fetch_resource(resource, response):
    """Add link methods with an on_fetched_resource hook."""
    if isinstance(resource_auth(resource), AmivTokenAuth):
        # Item links
        for item in response['_items']:
            add_methods_to_item_links(resource, item)

        # Resource links
        add_methods_to_resource_links(resource, response)


def _get_data(response):
    """Get response data as dict.

    Encoding/Decoding necessary for compatibility with both python 2 and 3.
    """
    return json.loads(response.get_data().decode('utf-8'))


def _set_data(response, data):
    """Jsonify dict and set as response data."""
    response.set_data(json.dumps(data))


def add_permitted_methods_after_update(resource, request, response):
    """Add link methods with an on_post_PATCH hook.

    The on_updated hook doesn't work since it doesn't include the links.

    This hook will also be called for errors which do not contain _links.
    => Make sure to only add methods for successful patches (status 200 only)
    """
    if (response.status_code == 200) and \
            isinstance(resource_auth(resource), AmivTokenAuth):
        item_data = _get_data(response)

        add_methods_to_item_links(resource, item_data)

        _set_data(response, item_data)


def add_permitted_methods_for_home(resource, request, response):
    """Add link methods to home endpoint with an on_post_GET hook.

    The home endpoint doesn't call any database hooks and no on_pre_GET hook.
    Therefore authentication needs to be done manually so we can check
    permissions.
    """
    if resource is None:
        authenticate()

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
                if isinstance(resource_auth(res_name), AmivTokenAuth):
                    check_if_admin(res_name)
                    res_link['methods'] = _get_resource_methods(res_name)

            _set_data(response, data)
