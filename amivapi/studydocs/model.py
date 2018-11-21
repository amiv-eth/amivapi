# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Model for studydocuments."""

from amivapi.settings import DEPARTMENT_LIST

from .authorization import StudydocsAuth


description = ("""
Study-documents are all documents users want to share with other users
related to their studies (i.e. no personal documents).

This covers a wide range of files, from lecture material over old exams to
cheatsheets. Because of this diversity, there are no strict file categories.

Instead, multiple metadata fields such as `semester` or `professor` exist
which can be used (if they are relevant for the files) to allow other users
to find documents more easily. The more fields are provided, the better.
All fields that do not apply can be `Null`.

<br />

## Security

In addition to the usual
[permissions](#section/Authentication-and-Authorization/Authorization),
file uploaders have additional permissions:

- **Users** can modify all items they uploaded themselves (identified by the
  user id in the `uploader` field).

- **Admins** can modify items for all users.
""")


studydocdomain = {
    'studydocuments': {
        'resource_title': "Study Documents",
        'item_title': "Study Document",

        'description': description,

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': StudydocsAuth,

        'mongo_indexes': {
            # Create indices for all meta fields to optimize filtering
            field: ([(field, 1)], {'background': True})
            for field in ('author', 'departement', 'lecture', 'professor',
                          'semester', 'type', 'course_year')
        },

        'schema': {
            'title': {
                'description': 'The title of the file bundle.',
                'example': 'Zusammenfassung',

                'required': True,
                'type': 'string',
                'empty': False,
                'maxlength': 100,
                'no_html': True
            },
            'files': {
                'description': 'The files to download, can be any format.',
                'example': ['(File)', '(Another File)'],

                'type': 'list',
                'schema': {
                    'type': 'media'
                },
                'required': True
            },

            'uploader': {
                'description': 'The user who uploaded the files (read-only).',
                'example': 'ea059fa90df4703316da25d8',

                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                },
                # Must be nullable: e.g. if root user uploads there is no user
                'nullable': True,
                'readonly': True,

            },
            'author': {
                'description': 'Original author of the uploaded files '
                               '(professor, assistant, copyright owner)',
                'example': "Pablo",

                'type': 'string',
                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None,
                'no_html': True
            },
            'department': {
                'example': DEPARTMENT_LIST[0],
                'type': 'string',
                'nullable': True,
                'default': None,
                'allowed': DEPARTMENT_LIST
            },

            'lecture': {
                'example': 'Advanced REST APIs',
                'maxlength': 100,
                'nullable': True,
                'default': None,
                'type': 'string',
                'no_html': True
            },

            'professor': {
                'example': 'Professor E. Xample',

                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None,
                'type': 'string',
                'no_html': True
            },
            'semester': {
                'description': 'The Semester for which the course/lecture/... '
                               'is offered, e.g. a first-semester course (1) '
                               'or a third-year/master course (5+).',
                'example': '5+',

                'type': 'string',
                'nullable': True,
                'default': None,
                'allowed': ['1', '2', '3', '4', '5+'],

            },
            'type': {
                'example': 'cheat sheets',
                'type': 'string',
                'nullable': True,
                'default': None,
                'allowed': ['exams', 'cheat sheets', 'lecture documents',
                            'exercises']
            },
            'course_year': {
                'type': 'integer',
                'example': 2018,
                'nullable': True,
                'default': None,
                'description': 'The year in which the course *was taken*, '
                               'to separate older from newer files.',
            }
        },
    }
}
