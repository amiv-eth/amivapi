# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""User Auth class."""

from bson import ObjectId

from flask import current_app
from eve.methods.patch import patch_internal

from amivapi.auth import AmivTokenAuth


class UserAuth(AmivTokenAuth):
    """Provides auth for /users resource.

    Main Goals:

    - Registered users can see nethz/name of everyone, full data of themselves
    - Registered users can change their own data (nobody else)


    We dont have to care about:

    - Admins, since for them no filters etc are applied
    - Unregistered users, since no methods are public.
    """

    def has_write_permission(self, user_id, item):
        """Check if *user* is allowed to write *item*.

        This includes PATCH and DELETE.

        User can only write his own data.

        Args:
            user (str): The id of the user that wants to access the item
            item (dict): The item the user wants to change or delete.

        Returns:
            bool: True if user has permission to change the item, False if not.
        """
        return item['_id'] == user_id

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
            return None


def hide_fields(resource, response):
    """Hide everything but id, nethz and name from others on get requests.

    The user can only see his personal data completely.

    Do nothing if auth is disabled.
    """
    pass


# Password hashing and verification


def verify_password(user, plaintext):
    """Check password of user, rehash if necessary.

    It is possible that the password is None, e.g. if the user is authenticated
    via LDAP. In this case default to "not verified".

    Args:
        user (dict): the user in question.
        plaintext (string): password to check

    Returns:
        bool: True if password matches. False if it doesn't or if there is no
            password set and/or provided.
    """
    password_context = current_app.config['PASSWORD_CONTEXT']

    if (plaintext is None) or (user['password'] is None):
        return False

    is_valid = password_context.verify(plaintext, user['password'])

    if is_valid and password_context.needs_update(user['password']):
        # update password - hook will handle hashing
        update = {'password': plaintext}
        patch_internal("users", payload=update, _id=user['_id'])
    return is_valid


def _hash_password(user):
    """Helper function to hash password.

    If password key doesn't exist or if value is None do nothing.

    If exists replace plaintext with hashed value.

    Args:
        user (dict): dict of user data.
    """
    password_context = current_app.config['PASSWORD_CONTEXT']

    if user.get('password', None) is not None:
        user['password'] = password_context.encrypt(user['password'])


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
        items (list): List of new items as passed by the on_insert event.
    """
    _hash_password(updates)
