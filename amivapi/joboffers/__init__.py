# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Joboffers module.

Since there are no hooks or anything, everything is just in here.
"""
from amivapi.utils import register_domain


description = ("""\
A job offer from a company, published by the organization.

## Internationalization

Job offers support both german and english titles and descriptions.
At least one language is required, but if possible, both english and german
versions should be included.

## Images

While the API generally accepts both `form-data` and JSON-input,
JSON cannot be used to upload files, such as the company logo.
You must use [`multipart/form-data`][1] to be able to send files.

[1]: https://www.w3.org/TR/html5/sec-forms.html#multipart-form-data
""")


jobdomain = {
    'joboffers': {
        'resource_title': "Job Offers",
        'item_title': "Job Offer",

        'description': description,

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'public_item_methods': ['GET', 'HEAD'],
        'public_methods': ['GET', 'HEAD'],

        'schema': {
            'company': {
                'description': 'The company offering the job.',
                'example': 'Popular Products AG',

                'required': True,
                'maxlength': 30,
                'type': 'string',
                'no_html': True,
            },
            'logo': {
                'description': 'Company logo (`.jpeg` or `.png`).',
                'example': '(File)',

                'filetype': ['png', 'jpeg'],
                'type': 'media',
                'required': True,
            },

            'title_de': {
                'title': 'German Title',
                'description': 'The title of the job offer in German.',
                'example': 'Rest API Entwickler (100%)',

                'type': 'string',
                'maxlength': 100,
                'required_if_not': 'title_en',
                'dependencies': ['description_de'],
                'no_html': True,
                'nullable': True,
                'default': None,
            },
            'title_en': {
                'title': 'English Title',
                'description': 'The title of the job offer in English.',
                'example': 'Rest API Developer (100%)',

                'type': 'string',
                'maxlength': 100,
                'required_if_not': 'title_de',
                'dependencies': ['description_en'],
                'no_html': True,
                'nullable': True,
                'default': None,
            },
            'description_de': {
                'title': 'German Description',
                'description': 'German description of the offered job, can '
                               'include Markdown syntax (without html tags). ',
                'example': 'Die Popular Products AG sucht Mitarbeiter ...',

                'type': 'string',
                'maxlength': 10000,
                'no_html': True,
                'nullable': True,
                'default': None,
            },
            'description_en': {
                'title': 'English Description',
                'description': 'English description of the offered job, can '
                               'include Markdown syntax (without html tags).',
                'example': 'The Popular Products AG is hiring ...',

                'type': 'string',
                'maxlength': 10000,
                'no_html': True,
                'nullable': True,
                'default': None,
            },


            'pdf': {
                'title': 'File',
                'description': 'The job offer as `.pdf` to download.',

                'filetype': ['pdf'],
                'type': 'media',
                'nullable': True,
                'default': None,
            },

            'time_end': {
                'title': 'Advertising End',
                'description': 'Time when the job offer is no longer '
                               'relevant.',
                'example': '2018-10-10T12:00:00Z',

                'type': 'datetime',
                'required': True,
            },
            'show_website': {
                'title': 'Show on Website',
                'description': 'Whether to display this offer on the website, '
                               'can be used to hide offers which are not yet '
                               'complete or similar.',

                'type': 'boolean',
                'default': False,
            }
        }
    }
}


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, jobdomain)
