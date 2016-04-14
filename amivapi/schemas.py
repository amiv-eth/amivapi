# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from sqlalchemy.ext.declarative import DeclarativeMeta

from amivapi.utils import make_domain, EMAIL_REGEX
from amivapi.db_utils import Base

from events import Event, EventSignup

def get_domain():
    domain = {}

    # generate from model
    for model in Base._decl_class_registry.values():
        if not isinstance(model, DeclarativeMeta):
            continue

        # Exlude resources already put in modules
        if model in [Event, EventSignup]:
            continue

        domain.update(make_domain(model))

    # Now some modifications are required for each resource:

    # general email fields

    # Only accept email addresses for email fields
    domain['users']['schema']['email'].update(
        {'regex': EMAIL_REGEX})

    # /users
    # Not patchable fields
    for field in ['firstname', 'lastname', 'legi', 'nethz', 'department',
                  'phone', 'gender', 'membership']:
        domain['users']['schema'][field].update(
            {'not_patchable_unless_admin': True})

    # Hide passwords
    domain['users']['datasource']['projection']['password'] = 0

    # TODO: enums of sqlalchemy should directly be caught by the validator
    domain['users']['schema']['gender'].update({
        'allowed': ['male', 'female']
    })
    domain['users']['schema']['department'].update({
        'allowed': ['itet', 'mavt'],
    })
    domain['users']['schema']['nethz'].update({
        'empty': False,
    })

    # Make it possible to retrive a user with his nethz (/users/nethz)
    domain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'nethz',
        }
    })

    # /sessions

    # POST will be handled by custom endpoint
    domain['sessions']['resource_methods'] = ['GET']

    # /groups

    # jsonschema validation for permissions
    domain['groups']['schema']['permissions'].update({
        'type': 'permissions_jsonschema'
    })

    # /groupaddresses
    domain['groupaddresses']['schema']['group_id'].update({
        'only_groups_you_moderate': True,
        'unique_combination': ['email'],
        'not_patchable': True,
    })
    domain['groupaddresses']['schema']['email'].update({
        'regex': EMAIL_REGEX,
        'unique_combination': ['group_id']})

    # /groupforwards
    domain['groupforwards']['schema']['group_id'].update({
        'only_groups_you_moderate': True,
        'unique_combination': ['email'],
        'not_patchable': True,
    })
    domain['groupforwards']['schema']['email'].update({
        'regex': EMAIL_REGEX,
        'unique_combination': ['group_id']})

    # /groupmembers

    domain['groupmembers']['schema']['user_id'].update({
        'only_self_enrollment_for_group': True,
        'unique_combination': ['group_id']})
    domain['groupmembers']['schema']['group_id'].update({
        'self_enrollment_must_be_allowed': True,
        'unique_combination': ['user_id']})

    # Membership is not transferable -> remove PUT and PATCH
    domain['groupmembers']['item_methods'] = ['GET', 'DELETE']

    # /files

    # No Patching for files
    domain['files']['item_methods'] = ['GET', 'PUT', 'DELETE']
    domain['files']['schema'].update({
        'data': {'type': 'media', 'required': True}
    })

    # /joboffers

    domain['joboffers']['schema'].update({
        'logo': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'pdf': {'type': 'media', 'filetype': ['pdf']},
    })

    # Add entry for storage so auth can find it

    domain['storage'] = {
        'resource_methods': ['GET'],
        'item_methods': ['GET'],
        'public_methods': [],
        'public_item_methods': [],
        'registered_methods': ['GET'],
        'description': {
            'general': 'Endpoint to download files, get the URLs via /files'
        }
    }

    return domain
