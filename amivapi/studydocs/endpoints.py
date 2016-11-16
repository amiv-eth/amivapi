# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Resource description for studydocuments
"""

from .authorization import StudydocsAuth


studydocdomain = {
    'studydocuments': {
        'description': {
            'fields': {
                'semester': 'Study-Semester as an Integer starting with '
                'first semester Bachelor.',
                'uploader': 'Read-only field describing which AMIV member '
                'uploaded the files',
                'author': 'Original author of the uploaded files'
                '(Prof, Assistant, copyright owner)',
                'coursesemester': 'Course Semester as Enum(HS/FS)+Integer'
            },
            'general': 'Study-documents are basically all documents that '
            'are connected to a course. All metadata is optional and intended '
            'to help finding the file. There are no strict categories, as those'
            ' do not work well for courses available to many departements and '
            'aiming at all levels of experience.'
        },

        'resource_methods': ['GET', 'POST', 'DELETE'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': StudydocsAuth,

        'schema': {
            'uploader': {
                'data_relation': {
                    'resource': 'users'
                },
                'nullable': True,
                'readonly': True,
                'type': 'objectid'
            },
            'author': {
                'maxlength': 100,
                'nullable': True,
                'type': 'string'
            },
            'department': {
                'maxlength': 4,
                'nullable': True,
                'type': 'string'
            },
            'files': {
                'type': 'list',
                'schema': {
                    'type': 'media'
                },
                'required': True
            },
            'lecture': {
                'maxlength': 100,
                'nullable': True,
                'type': 'string'
            },
            'name': {
                'maxlength': 100,
                'nullable': True,
                'type': 'string'
            },
            'professor': {
                'maxlength': 100,
                'nullable': True,
                'type': 'string'
            },
            'semester': {
                'nullable': True,
                'type': 'integer'
            },
            'type': {
                'maxlength': 30,
                'nullable': True,
                'type': 'string'
            },
            'coursesemester': {
                    'maxlength': 5,
                    'nullable': True,
                    'type': 'string'
            }
        },
    }
}
