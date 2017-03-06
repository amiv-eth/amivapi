# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Joboffers module.

Since there are no hooks or anything, everything is just in here.
"""

from amivapi.utils import register_domain


jobdomain = {
    'joboffers': {
        'description': 'A Job Offer posts repository Users can post a job offer'
        ' with the necessary content to fill out a job offer advertisement',

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'public_item_methods': ['GET'],
        'public_methods': ['GET'],

        'schema': {
            'company': {
                'maxlength': 30,
                'type': 'string',
            },
            'description_de': {
                'type': 'string',
            },
            'description_en': {
                'type': 'string'
            },
            'logo': {
                'filetype': ['png', 'jpeg'],
                'type': 'media',
                'required': True
            },
            'pdf': {
                'filetype': ['pdf'],
                'type': 'media',
                'required': True
            },
            'time_end': {
                'type': 'datetime'
            },
            'title_de': {
                'type': 'string',
                'required_if_not': 'title_en',
                'dependencies': 'description_de'
            },
            'title_en': {
                'type': 'string',
                'required_if_not': 'title_de',
                'dependencies': 'description_en'
            },
            'show_website': {
                'type': 'boolean',
                # TODO: Activate this, when it is possible to post files and
                # boolean in the same request
                # Currently this is not possible and therefore this would
                # prevent POST to /joboffers
                # 'required': True,
                'default': False
            }
        }
    }
}


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, jobdomain)
