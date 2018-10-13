# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Model for studydocuments."""

from amivapi.settings import DEPARTMENT_LIST

from .authorization import StudydocsAuth


studydocdomain = {
    'studydocuments': {

        'description': 'Study-documents are basically all documents that are '
        'connected to a course. Most metadata is optional and intended to '
        'help finding the file. There are no strict categories, as those do '
        'not work well for courses available to many departements and aiming '
        'at all levels of experience.',

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': StudydocsAuth,

        'mongo_indexes': {
            'departement': ([('departement', 1)], {'background': True}),
            'lecture': ([('lecture', 1)], {'background': True}),
            'professor': ([('professor', 1)], {'background': True}),
            'semester': ([('semester', 1)], {'background': True})
        },

        'schema': {
            'uploader': {
                'type': 'objectid',
                'data_relation': {'resource': 'users'},
                # Must be nullable: e.g. if root user uploads there is no user
                'nullable': True,
                'readonly': True,
                'description': 'Read-only field describing which AMIV member '
                'uploaded the files'
            },
            'author': {
                'type': 'string',
                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'description': 'Original author of the uploaded files'
                '(Prof, Assistant, copyright owner)',
                'no_html': True
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
                'type': 'string',,
                'no_html': True
            },
            'title': {
                'type': 'string',
                'empty': False,
                'maxlength': 100,
                'no_html': True
            },
            'professor': {
                'maxlength': 100,
                'nullable': True,
                'type': 'string',
                'no_html': True
            },
            'semester': {
                'type': 'string',
                'nullable': True,
                'allowed': ['1', '2', '3', '4', '5+'],
                'description': 'Study-Semester of the lecture starting with '
                'first semester Bachelor.'
            },
            'type': {
                'type': 'string',
                'allowed': ['exams', 'cheat sheets', 'lecture documents',
                            'exercises']
            },
            'course_year': {
                'type': 'integer',
                'description': 'Course Year as Integer'
            }
        },
    }
}
