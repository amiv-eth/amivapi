# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Joboffers module.

Since there are no hooks or anything everything is just in here.
"""

from amivapi.utils import register_domain


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, jobdomain)


jobdomain = {'joboffers': {
    'datasource': {'projection': {'_author': 1,
                                  'company': 1,
                                  'description_de': 1,
                                  'description_en': 1,
                                  'id': 1,
                                  'logo': 1,
                                  'pdf': 1,
                                  'time_end': 1,
                                  'title_de': 1,
                                  'title_en': 1},
                   'source': 'JobOffer'},
    'description': {},
    'item_lookup': True,
    'item_lookup_field': '_id',
    'item_url': 'regex("[0-9]+")',
    'owner': [],
    'owner_methods': [],
    'public_item_methods': ['GET'],
    'public_methods': ['GET'],
    'registered_methods': [],
    'schema': {
        '_author': {'data_relation': {'resource': 'users'},
                    'nullable': True,
                    'readonly': True,
                    'type': 'objectid'},
        'company': {'maxlength': 30,
                    'nullable': True,
                    'type': 'string'},
        'description_de': {'nullable': True,
                           'type': 'string',
                           'unique': False},
        'description_en': {'nullable': True,
                           'type': 'string'},
        'logo': {'filetype': ['png', 'jpeg'],
                 'type': 'media'},
        'pdf': {'filetype': ['pdf'],
                'type': 'media'},
        'time_end': {'nullable': True,
                     'type': 'datetime'},
        'title_de': {'nullable': True,
                     'type': 'string'},
        'title_en': {'nullable': True,
                     'type': 'string'}
    }
}}
