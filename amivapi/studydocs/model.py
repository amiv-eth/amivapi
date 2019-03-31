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

<br />

## Ratings

TODO!

<br />

## Summary

For more efficient searching of study documents, a *summary* of available
metadata fields is returned in a `_summary` field of the response,
which contains additional information on metadata fields.
It lists all distinct values for each field along with the number of
documents available.

```
_summary:
    professor:
        Prof. Dr. Awesome: 10
        Prof. Okay: 5
        ...
    lecture:
        ...
    ...
```

The summary is only computed for documents matching the current `where` query,
e.g. when searching for ITET documents, only professors related to ITET
documents will show up in the summary.
""")


class StudyDocValidator(object):
    """Custom Validator to register `allow_summary` property."""

    def _validate_allow_summary(self, *args, **kwargs):
        """{'type': 'boolean'}"""


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
                'no_html': True,
                'allow_summary': True,
            },
            'department': {
                'example': DEPARTMENT_LIST[0],
                'type': 'string',
                'nullable': True,
                'default': None,
                'allowed': DEPARTMENT_LIST,
                'allow_summary': True,
            },

            'lecture': {
                'example': 'Advanced REST APIs',
                'maxlength': 100,
                'nullable': True,
                'default': None,
                'type': 'string',
                'no_html': True,
                'allow_summary': True,
            },

            'professor': {
                'example': 'Professor E. Xample',

                'maxlength': 100,
                'empty': False,
                'nullable': True,
                'default': None,
                'type': 'string',
                'no_html': True,
                'allow_summary': True,
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
                'allow_summary': True,

            },
            'type': {
                'example': 'cheat sheets',
                'type': 'string',
                'nullable': True,
                'default': None,
                'allowed': ['exams', 'cheat sheets', 'lecture documents',
                            'exercises'],
                'allow_summary': True,
            },
            'course_year': {
                'type': 'integer',
                'example': 2018,
                'nullable': True,
                'default': None,
                'description': 'The year in which the course *was taken*, '
                               'to separate older from newer files.',
                'allow_summary': True,
            },

            'rating': {
                'title': 'Study Document Rating',
                'description': 'The study document rating as a fraction of '
                               'upvotes divided by all votes. Computed using '
                               'a confidence interval. Null if no votes have '
                               'been cast.',
                'example': '0.9',

                'type': 'float',
                'readonly': True,
            },
        },
    },

    'studydocratings': {
        'resource_title': "Study Document Rating",
        'item_title': "Study Document Rating",

        'description': "Rating for Study documents (TODO)",

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

         # TODO
        'authentication': StudydocsAuth,

        'schema': {
            'user': {
                'description': 'The rating user.',
                'example': '679ff66720812cdc2da4fb4a',

                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                    'cascade_delete': True,
                },
                'not_patchable': True,
                'required': True,
                'unique_combination': ['studydoc'],
            },

            'studydoc': {
                'title': 'Study Document',
                'description': 'The rated study doc.',
                'example': '10d8e50e303049ecb856ae9b',

                'data_relation': {
                    'resource': 'studydocuments',
                    'embeddable': True,
                    'cascade_delete': True,
                },
                'not_patchable': True,
                'required': True,
                'type': 'objectid',
            },
            'rating': {
                'description': 'The given rating, can be an up- or downvote.',
                'example': 'up',

                'type': 'string',
                'allowed': ['up', 'down'],
                'required': True
            },
        },
    }

}
