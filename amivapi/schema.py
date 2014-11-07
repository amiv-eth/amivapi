from amivapi import models

RESOURCES = {

    # Member APIs
    'users': models.User._eve_schema['users'],
    'groups': models.Group._eve_schema['groups'],
    'emails': models.EmailForward._eve_schema['emails'],
    'sessions': models.Session._eve_schema['sessions'],

    # Event APIs
    'events': models.Event._eve_schema['events'],
    'signups': models.EventSignup._eve_schema['signups'],

    # File APIs
    'files': models.File._eve_schema['files'],
    'studydocuments': models.StudyDocument._eve_schema['studydocuments'],

    # Jobs API
    'joboffers': models.JobOffer._eve_schema['joboffers'],

    # Explicit, more detailed version of the above:
    # =============================================
    #
    # 'users': {
    #     'datasource': {
    #         'source': models.User.__name__,
    #     },
    #     'embedded_fields': ['groups'],
    #     'schema': {
    #         'firstname': {
    #             'type': "string",
    #             'required': True,
    #             'empty': False,
    #         },
    #         'lastname': {
    #             'type': "string",
    #             'required': True,
    #             'empty': False,
    #         },
    #         'birthday': {
    #             'type': "datetime",
    #         },
    #         'legi': {
    #             'type': "string",
    #             'minlength': 8,
    #             'maxlength': 8,
    #             'readonly': True,
    #         },
    #         'rfid': {
    #             'type': "string",
    #             'minlength': 6,
    #             'maxlength': 6,
    #             'nullable': True,
    #             'regex': "^\d{6}$",
    #             'unique': True,
    #         },
    #         'nethz': {
    #             'type': "string",
    #             'readonly': True,
    #         },
    #         'department': {
    #             'type': "string",
    #             'readonly': True,
    #         },
    #         'phone': {
    #             'type': "string",  # TODO: add 'phone' validator
    #             'nullable': True,
    #             'unique': True,
    #         },
    #         'ldapAddress': {
    #             'type': "string",
    #             'readonly': True,
    #         },
    #         'gender': {
    #             'type': "string",
    #             'allowed': ["male", "female"],
    #             'required': True,
    #         },
    #         'email': {
    #             'type': "string",  # TODO: add 'phone' validator
    #             'required': True,
    #             'empty': False,
    #             'unique': True,
    #         },
    #         'membership': {
    #             'type': "string",
    #             'allowed': ["none", "regular", "extraordinary", "honorary"],
    #             'required': True,
    #         },
    #         'groups': {
    #             'type': "list",
    #             'items': [{'type': "integer"}],
    #             'data_relation': {
    #                 'resource': "groups",
    #                 'field': ID_FIELD,
    #                 'embeddable': True,
    #             },
    #         },
    #         'services': {
    #             'type': "dict",
    #             'schema': {
    #                 'beer': {
    #                     'type': "integer",
    #                     'min': 0,
    #                     'max': 16,
    #                     'default': 0,
    #                 },
    #                 'coffee': {
    #                     'type': "integer",
    #                     'min': 0,
    #                     'max': 16,
    #                     'default': 0,
    #                 },
    #             },
    #         },
    #     },
    # },
}
