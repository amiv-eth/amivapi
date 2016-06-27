# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module."""

from flask import current_app

from eve.methods.patch import patch_internal

from amivapi.utils import register_domain, EMAIL_REGEX

userdomain = {
    'users': {
        'description': {'general': 'In general, the user data will be '
                        'generated from LDAP-Data. However, one might change '
                        'the RFID-Number or the membership-status. '
                        'Extraordinary members may not have a LDAP-Account '
                        'and can therefore access all given fields.',
                        'methods': {'GET': 'Authorization is required for '
                                    'most of the fields'}},

        'additional_lookup': {'field': 'nethz',
                              'url': 'regex(".*[\\w].*")'},

        'datasource': {'projection': {'password': 0}},

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        # 'owner': ['id'],
        # 'owner_methods': ['GET', 'PATCH'],

        'schema': {
            'nethz': {
                'type': 'string',
                'empty': False,
                'nullable': True,
                'maxlength': 30,
                'not_patchable_unless_admin': True,
                'unique': True,
                'default': None},  # Do multiple none values work?
            'firstname': {
                'type': 'string',
                'maxlength': 50,
                'empty': False,
                'nullable': False,
                'not_patchable_unless_admin': True,
                'required': True},
            'lastname': {
                'type': 'string',
                'maxlength': 50,
                'empty': False,
                'nullable': False,
                'not_patchable_unless_admin': True,
                'required': True},
            'membership': {
                'allowed': ["none", "regular", "extraordinary", "honorary"],
                'maxlength': 13,
                'not_patchable_unless_admin': True,
                'required': True,
                'type': 'string',
                'unique': False},

            # Values only imported by ldap
            'legi': {
                'maxlength': 8,
                'not_patchable_unless_admin': True,
                'nullable': True,
                'required': False,
                'type': 'string',
                'unique': True},
            'department': {
                'type': 'string',
                'allowed': ['itet', 'mavt'],
                'not_patchable_unless_admin': True,
                'nullable': True},
            'gender': {
                'type': 'string',
                'allowed': ['male', 'female'],
                'maxlength': 6,
                'not_patchable_unless_admin': True,
                'required': True,
                'unique': False},

            # Fields the user can modify himself
            'password': {
                'type': 'string',
                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None},
            'email': {
                'type': 'string',
                'maxlength': 100,
                'regex': EMAIL_REGEX,
                'required': True,
                'unique': True},
            'rfid': {
                'type': 'string',
                'maxlength': 6,
                'empty': False,
                'nullable': True,
                'unique': True},
            'phone': {
                'type': 'string',
                'maxlength': 20,
                'empty': False,
                'nullable': True},
            'send_newsletter': {
                'type': 'boolean',
                'nullable': True},
        }
    }
}


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
        # rehash password
        update = {'password': password_context.encrypt(plaintext)}
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


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, userdomain)

    app.on_insert_users += hash_on_insert
    app.on_update_users += hash_on_update
    app.on_replace_user += hash_on_update
