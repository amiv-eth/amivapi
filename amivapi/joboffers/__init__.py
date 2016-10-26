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
            'description': {
                'fields': {
                },
                'general': 'A Job Offer posts repository'
                'Users can post a job offer with the necessary'
                'content to fill out a job offer advertisement'
            },

            'resource_methods': ['GET', 'POST'],
            'item_methods': ['GET', 'PATCH', 'DELETE'],

            'public_item_methods': ['GET'],
            'public_methods': ['GET'],

            'schema': {
                'company': {
                    'required': True,
                    'maxlength': 30,
                    'nullable': True,
                    'type': 'string',
                    
                    # This is basically here, because this is a required
                    # field. It will make sure there is always either an english
                    # or a german title
                    'depends_any': ['title_de', 'title_en']                
                },
                'description_de': {
                    'nullable': True,
                    'type': 'string',
                    'unique': False
                },
                'description_en': {
                    'nullable': True,
                    'type': 'string'
                },
                'logo': {
                    'filetype': ['png', 'jpeg'],
                    'type': 'media'
                },
                'pdf': {
                    'filetype': ['pdf'],
                    'type': 'media'
                },
                'time_end': {
                    'nullable': True,
                    'type': 'datetime'
                },
                'title_de': {
                    'nullable': True,
                    'type': 'string'
                },
                'title_en': {
                    'nullable': True,
                    'type': 'string'
                }
            }
        }
    }


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, jobdomain)
