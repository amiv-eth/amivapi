# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""User Auth class."""

from bson import ObjectId

from flask import current_app, g

from amivapi.auth import AmivTokenAuth
from amivapi.utils import on_post_hook


class UserAuth(AmivTokenAuth):
    """Provides auth for /users resource.

    This is an example of how to implement the AmivTokenAuth.

    Main Goals:

    - Registered users can see nethz/name of everyone, full data of themselves
    - Registered users can change their own data (nobody else)


    We dont have to care about:

    - Admins, since for them no filters etc are applied
    - Unregistered users, since no methods are public.

    Since only admins can POST, we do not need to implement a custom
    `has_resource_write_permission` - the default is fine.
    """

    def has_item_write_permission(self, user_id, item):
        """Check if *user* is allowed to write *item*.

        This includes PATCH and DELETE.

        User can only write his own data.

        Args:
            user (str): The id of the user that wants to access the item
            item (dict): The item the user wants to change or delete.

        Returns:
            bool: True if user has permission to change the item, False if not.
        """
        return str(item['_id']) == user_id

    def create_user_lookup_filter(self, user_id):
        """Create a filter for item lookup.

        Not a member: Can see only himself
        A Member: Can see everyone

        Note: Users will only see complete info for themselves.
        But excluding other fields will be done in a hook later.

        Args:
            user_id (str): Id of the user. No public methods -> wont be None

        Returns:
            dict: The filter, will be combined with other filters in the hook.
                Return None if no filters should be applied.
        """
        # Find out if not member
        collection = current_app.data.driver.db['users']
        # set projection to only return membership
        result = collection.find_one({'_id': ObjectId(user_id)},
                                     {'membership': 1})

        if result['membership'] == "none":
            # Can't see others
            return {'_id': user_id}
        else:
            # Can see everyone (fields will be filtered later)
            return {}


@on_post_hook
def hide_after_request(request, response, payload):
    """Hide user fields after all requests to /users.

    Wrapper around `hide_fields` to work reliably with GET, POST as well as
    PATCH.

    Args:
        request, response: unused
        payload (dict): response data
    """
    # Use either the '_items' field (resource requests) or the
    # whole payload as one item (item requests)
    for item in payload.get('_items', [payload]):
        hide_fields(item)


def hide_fields(item):
    """Show only meta fields, nethz and name from others in response.

    The user can only see his personal data completely.

    Nobody can see passwords.

    Args:
        item (dict): User data
    """
    # Always remove password
    item.pop('password', None)

    # Remove other fields
    if not (g.get('resource_admin') or
            g.get('resource_admin_readonly') or
            g.get('current_user') == str(item['_id'])):
        for key in list(item):
            if (key[0] != '_' and
                    key not in ('firstname', 'lastname', 'nethz')):
                item.pop(key)


def restrict_filters(*_):
    """If the user is not an admin, restrict the query filters.

    Changing the config modifies subsequent requests, so we need to set
    it explicitly for each request.
    """
    userdomain = current_app.config['DOMAIN']['users']
    if not (g.get('resource_admin') or g.get('resource_admin_readonly')):
        userdomain['allowed_filters'] = [
            '_id', '_etag', '_updated', '_created', '_links',
            'firstname', 'lastname', 'nethz',
        ]
    else:
        userdomain['allowed_filters'] = ['*']


# Project password status

def project_password_status(response):
    """Add a boolean field password_state to the response.

    This function must be applied before hide_fields, as it uses the password
    field.

    Args:
        response: Response object of the request
    """
    # Compatibility with both item and resource hook
    items = response.get('_items', [response])

    for item in items:
        item['password_set'] = item.get('password') is not None


def project_password_status_on_inserted(items):
    """Add a boolean field password_state to the response.

    This function must be applied before hide_fields, as it uses the password
    field.

    Args:
        items (list): List of new items as passed by the on_inserted event.
    """
    for item in items:
        item['password_set'] = item.get('password') is not None


def project_password_status_on_updated(updates, original):
    """Add a boolean field password_state to the response.

    This function must be applied before hide_fields, as it uses the password
    field.

    Args:
        updates (dict): dict of changed user data
        original (dict): dict of user data before the update
    """
    updates['password_set'] = updates.get('password') is not None


# Password hashing

def _hash_password(user):
    """Helper function to hash password.

    If password key doesn't exist or if value is None do nothing.

    If exists replace plaintext with hashed value.

    Args:
        user (dict): dict of user data.
    """
    password_context = current_app.config['PASSWORD_CONTEXT']

    if user.get('password', None) is not None:
        user['password'] = password_context.hash(user['password'])


def hash_on_insert(items):
    """Hook for user insert.

    Hash the password if it is not None.
    (When logging in via LDAP the password should not be stored and therefore
    it can be none.)

    Args:
        items (list): List of new items as passed by the on_insert event.
    """
    for user in items:
        _hash_password(user)


def hash_on_update(updates, original):
    """Hook for user update or replace.

    Hash the password if it is not None.
    (When logging in via LDAP the password should not be stored and therefore
    it can be none.)

    Args:
        updates (dict): dict of changed user data
        original (dict): dict of user data before the update
    """
    _hash_password(updates)
