# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event resource settings.

Contains mode and function to create schema.
As soon as we switch to mongo this will only have the schema.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Unicode,
    Integer,
    CHAR,
    Enum)
from sqlalchemy.orm import relationship

from amivapi.utils import Base


class StudyDocument(Base):
    """StudyDocument Model."""

    __description__ = {
        'general': "Study-documents are basically all documents that are "
        "connected to a course. This resource provides meta-data for the "
        "assigned files.",
        'fields': {
            'semester': "Study-Semester as an Integer starting with first "
            "semester Bachelor."
        }
    }
    __expose__ = True
    __projected_fields__ = ['files']

    __owner__ = ['_author']
    __owner_methods__ = ['GET', 'PUT', 'PATCH', 'DELETE']
    __registered_methods__ = ['GET', 'POST']

    name = Column(Unicode(100))
    type = Column(Unicode(30))
    exam_session = Column(Unicode(10))
    department = Column(Enum("itet", "mavt"))
    lecture = Column(Unicode(100))
    professor = Column(Unicode(100))
    semester = Column(Integer)
    author_name = Column(Unicode(100))

    # relationships
    files = relationship("File", backref="study_doc",
                         cascade="all")


class File(Base):
    """This is a file that belongs to a study document.

    An additional name for the file is possible
    A studydocument needs to be referenced

    Files can only be created and deleted (or both, put), patching them is not
    intended
    """

    __expose__ = True

    __owner__ = ['_author']  # This permitts everybody to post here!
    __owner_methods__ = ['GET', 'PUT', 'DELETE']
    __registered_methods__ = ['GET']

    name = Column(Unicode(100))
    data = Column(CHAR(100))  # This will be modified in schemas.py!
    study_doc_id = Column(Integer, ForeignKey("studydocuments.id"),
                          nullable=False)


def make_studydocdomain():
    """Create domain.

    This is a function so it can be called after models in all modules have
    been defined.
    """

    studydocdomain = {
        'studydocuments': {
            'datasource': {
                'projection': {
                    '_author': 1,
                    'author_name': 1,
                    'department': 1,
                    'exam_session': 1,
                    'files': 1,
                    'id': 1,
                    'lecture': 1,
                    'name': 1,
                    'professor': 1,
                    'semester': 1,
                    'type': 1},
                'source': 'StudyDocument'},
            'description': {
                'fields': {
                    'semester': 'Study-Semester as an Integer starting with first semester Bachelor.'},
                'general': 'Study-documents are basically all documents that are connected to a course. This resource provides meta-data for the assigned files.'},
            'embedded_fields': {},
            'item_lookup': True,
            'item_lookup_field': '_id',
            'item_url': 'regex("[0-9]+")',
            'owner': ['_author'],
            'owner_methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
            'public_item_methods': [],
            'public_methods': [],
            'registered_methods': ['GET', 'POST'],
            'schema': {
                '_author': {
                    'data_relation': {
                        'resource': 'users'},
                    'nullable': True,
                    'readonly': True,
                    'type': 'objectid',
                    'unique': False},
                'author_name': {
                    'maxlength': 100,
                    'nullable': True,
                    'type': 'string'},
                'department': {
                    'maxlength': 4,
                    'nullable': True,
                    'type': 'string'},
                'exam_session': {
                    'maxlength': 10,
                    'nullable': True,
                    'type': 'string'},
                'files': {
                    'data_relation': {
                        'embeddable': True,
                        'resource': 'files'},
                    'type': 'objectid'},
                'lecture': {
                    'maxlength': 100,
                    'nullable': True,
                    'type': 'string'},
                'name': {
                    'maxlength': 100,
                    'nullable': True,
                    'type': 'string'},
                'professor': {
                    'maxlength': 100,
                    'nullable': True,
                    'type': 'string'},
                'semester': {
                    'nullable': True,
                    'type': 'integer'},
                'type': {
                    'maxlength': 30,
                    'nullable': True,
                    'type': 'string'}},
            'sql_model': StudyDocument},
        'files': {
            'datasource': {
                'projection': {
                    '_author': 1,
                    'data': 1,
                    'id': 1,
                    'name': 1,
                    'study_doc': 0,
                    'study_doc_id': 1},
                'source': 'File'},
            'description': {},
            'item_lookup': True,
            'item_lookup_field': '_id',
            'item_url': 'regex("[0-9]+")',
            'owner': ['_author'],
            'owner_methods': ['GET', 'PUT', 'DELETE'],
            'public_item_methods': [],
            'public_methods': [],
            'registered_methods': ['GET'],
            'schema': {
                '_author': {
                    'data_relation': {
                        'resource': 'users'},
                    'nullable': True,
                    'readonly': True,
                    'type': 'objectid'},
                'data': {
                    'maxlength': 100,
                    'nullable': True,
                    'type': 'string'},
                'name': {
                    'maxlength': 100,
                    'nullable': True,
                    'type': 'string'},
                'study_doc': {
                    'data_relation': {
                        'embeddable': True,
                        'resource': 'studydocuments'},
                    'type': 'objectid'},
                'study_doc_id': {
                    'data_relation': {
                        'resource': 'studydocuments'},
                    'required': True,
                    'type': 'objectid'}},
            'sql_model': File}}

    #studydocdomain.update(make_domain(StudyDocument))
    #studydocdomain.update(make_domain(File))

    # No Patching for files
    studydocdomain['files']['item_methods'] = ['GET', 'PUT', 'DELETE']
    studydocdomain['files']['schema'].update({
        'data': {'type': 'media', 'required': True}
    })

    return studydocdomain