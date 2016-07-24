# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""User module."""

from flask import abort

from amivapi.utils import EMAIL_REGEX

from .security import UserAuth

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

        'authentication': UserAuth,

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


def prevent_projection(request, lookup):
    """Prevent extraction of password hashes.

    args:
        request: The request object
        lookup (dict): The lookup dict(unused)
    """
    projection = request.args.get('projection')
    if projection and 'password' in projection:
        abort(403, description='Bad projection field: password')
