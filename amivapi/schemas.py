# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from sqlalchemy.ext.declarative import DeclarativeMeta

from amivapi import models
from amivapi.utils import make_domain, EMAIL_REGEX


def get_domain():
    domain = {}

    # generate from model
    for model in models.Base._decl_class_registry.values():
        if not isinstance(model, DeclarativeMeta):
            continue

        domain.update(make_domain(model))

    # Now some modifications are required for each resource:

    # general email fields

    # Only accept email addresses for email fields
    domain['users']['schema']['email'].update(
        {'regex': EMAIL_REGEX})
    domain['eventsignups']['schema']['email'].update(
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

    # /events

    # additional validation
    domain['events']['schema']['additional_fields'].update({
        'type': 'json_schema'})
    domain['events']['schema']['price'].update({'min': 0})
    domain['events']['schema']['spots'].update({
        'min': -1,
        'if_this_then': ['time_register_start', 'time_register_end']})
    domain['events']['schema']['time_register_end'].update({
        'dependencies': ['time_register_start'],
        'later_than': 'time_register_start'})
    domain['events']['schema']['time_end'].update({
        'dependencies': ['time_start'],
        'later_than': 'time_start'})

    # time_end for /events requires time_start
    domain['events']['schema']['time_end'].update({
        'dependencies': ['time_start']
    })

    # event images
    domain['events']['schema'].update({
        'img_thumbnail': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_banner': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_poster': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_infoscreen': {'type': 'media', 'filetype': ['png', 'jpeg']}
    })

    # /eventsignups

    # POST done by custom endpoint
    domain['eventsignups']['resource_methods'] = ['GET']

    # schema extensions including custom validation
    domain['eventsignups']['schema']['event_id'].update({
        'not_patchable': True,
        'unique_combination': ['user_id', 'email'],
        'signup_requirements': True})
    domain['eventsignups']['schema']['user_id'].update({
        'not_patchable': True,
        'unique_combination': ['event_id'],
        'only_self_enrollment_for_event': True})
    domain['eventsignups']['schema']['email'].update({
        'not_patchable': True,
        'unique_combination': ['event_id'],
        'only_anonymous': True,
        'email_signup_must_be_allowed': True})

    # Since the data relation is not evaluated for posting, we need to remove
    # it from the schema TODO: EXPLAIN BETTER
    del(domain['eventsignups']['schema']['email']['data_relation'])
    # Remove _email_unreg and _token from the schema since they are only
    # for internal use and should not be visible
    del(domain['eventsignups']['schema']['_email_unreg'])
    del(domain['eventsignups']['schema']['_token'])

    domain['eventsignups']['schema']['additional_fields'].update({
        'type': 'json_event_field'})

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

    return domain
