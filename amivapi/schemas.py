# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.utils import make_domain, EMAIL_REGEX

from models import User, File, StudyDocument, JobOffer, Purchase


def get_domain():
    domain = {}

    # generate from models
    for model in [User, File, StudyDocument, JobOffer, Purchase]:
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
