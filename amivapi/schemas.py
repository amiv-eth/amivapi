# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from eve_sqlalchemy.decorators import registerSchema
from sqlalchemy.ext.declarative import DeclarativeMeta

from amivapi import models
from amivapi.settings import ROLES


def get_domain():
    domain = {}

    for model in models.Base._decl_class_registry.values():
        if not isinstance(model, DeclarativeMeta):
            continue

        tbl_name = model.__tablename__

        registerSchema(tbl_name)(model)
        domain.update(model._eve_schema)

        for field in model.__projected_fields__:
            domain[tbl_name]['datasource']['projection'].update(
                {field: 1}
            )

        domain[tbl_name]['public_methods'] = (model.__public_methods__)
        domain[tbl_name]['public_item_methods'] = (model.__public_methods__)

        # For documentation
        domain[tbl_name]['description'] = model.__description__

        # Users should not provide _author fields
        domain[tbl_name]['schema']['_author'].update({'readonly': True})

    # Make it possible to retrive a user with his nethz (/users/nethz)
    domain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'nethz',
        }
    })

    # Hide passwords

    domain['users']['datasource']['projection']['password'] = 0

    # Only accept email addresses for email fields
    EMAIL_REGEX = '^.+@.+$'
    domain['users']['schema']['email'].update(
        {'regex': EMAIL_REGEX})
    domain['groupaddressmembers']['schema']['email'].update(
        {'regex': EMAIL_REGEX})
    domain['eventsignups']['schema']['email'].update(
        {'regex': EMAIL_REGEX})

    # Permissions: Only allow existing roles and expiry date must be in the
    # future
    domain['permissions']['schema']['role'].update(
        {'allowed': list(ROLES.keys())})
    domain['permissions']['schema']['expiry_date'].update(
        {'future_date': True})

    """ For confirmation: eve will not handle POST """
    domain['groupaddressmembers']['resource_methods'] = ['GET']
    domain['eventsignups']['resource_methods'] = ['GET']

    domain[models.Session.__tablename__]['resource_methods'] = ['GET']

    # No Patching for files and no patching/put for
    # groupaddressmembers/usermembers
    domain[models.File.__tablename__]['item_methods'] = ['GET', 'PUT',
                                                         'DELETE']
    domain['groupaddressmembers']['item_methods'] = ['GET', 'DELETE']
    domain['groupusermembers']['item_methods'] = ['GET', 'DELETE']

    # time_end for /events requires time_start
    domain['events']['schema']['time_end'].update({
        'dependencies': ['time_start']
    })

    # enums of sqlalchemy should directly be catched by the validator
    domain['users']['schema']['gender'].update({
        'allowed': ['male', 'female']
    })
    domain['users']['schema']['department'].update({
        'allowed': ['itet', 'mavt']
    })
    domain['users']['schema']['nethz'].update({
        'empty': False
    })

    """
    Eventsignups, schema extensions including custom validation
    """
    domain['eventsignups']['schema']['event_id'].update({
        'not_patchable': True,
        'signup_requirements': True})
    domain['eventsignups']['schema']['user_id'].update({
        'not_patchable': True,
        'unique_combination': ['eventsignups', 'event_id'],
        'dependencies': ['event_id'],
        'public_check': 'event_id',
        'self_enroll': True})
    domain['eventsignups']['schema']['email'].update({
        'not_patchable': True,
        'unique_combination': ['eventsignups', 'event_id'],
        'dependencies': ['user_id'],
        'only_anonymous': True})
    # Since the data relation is not evaluated for posting, we need to remove
    # it from the schema TODO: EXPLAIN BETTER
    del(domain['eventsignups']['schema']['email']['data_relation'])
    # Remove _email_unreg and _token from the schema since they are only
    # for internal use and should not be visible
    del(domain['eventsignups']['schema']['_email_unreg'])
    del(domain['eventsignups']['schema']['_token'])

    domain['eventsignups']['schema']['additional_fields'].update({
        'type': 'json_event_field'})

    """
    Events, schema extensions
    """
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

    """
    Group user members and address members
    """
    domain['groupusermembers']['schema']['user_id'].update({
        'self_enroll_group': True,
        'dependencies': ['group_id']})

    """
    Filetype needs to be specified as media, maybe this can be automated
    """
    domain['events']['schema'].update({
        'img_thumbnail': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_banner': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_poster': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'img_infoscreen': {'type': 'media', 'filetype': ['png', 'jpeg']}
    })

    domain['files']['schema'].update({
        'data': {'type': 'media', 'required': True}
    })

    domain['joboffers']['schema'].update({
        'logo': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'pdf': {'type': 'media', 'filetype': ['pdf']},
    })

    return domain
