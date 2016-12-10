# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Model for studydocuments."""

from amivapi.settings import DEPARTMENT_LIST

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
                'course_year': 'Course Year'
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
                'type': 'objectid',
                'data_relation': {'resource': 'users'},
                # Must be nullable: e.g. if root user uploads there is no user
                'nullable': True,
                'readonly': True,
            },
            'author': {
                'type': 'string',
                'maxlength': 100,
                'nullable': True,
            },
            'department': {
                'type': 'string',
                'nullable': True,
                'allowed': DEPARTMENT_LIST
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
            'title': {
                'type': 'string',
                'empty': False,
                'maxlength': 100,
            },
            'professor': {
                'maxlength': 100,
                'nullable': True,
                'type': 'string'
            },
            'semester': {
                'nullable': True,
                'type': 'string',
                'allowed': ['1', '2', '3', '4', '5+']
            },
            'type': {
                'type': 'string',
                'allowed': ['exams', 'cheat sheets', 'lecture documents',
                            'exercises']
            },
            'course_year': {
                'type': 'integer'
            }
        },
    }
}
