from amivapi import models, permission_matrix
from eve_sqlalchemy.decorators import registerSchema
from inspect import getmembers, isclass


def load_domain(config):
    domain = config['DOMAIN'] = {}

    for cls_name, cls in getmembers(models):
        if(isclass(cls)
                and cls.__module__ == "amivapi.models"
                and cls.__expose__ is True):
            registerSchema(cls.__tablename__)(cls)
            domain.update(cls._eve_schema)

            for field in cls.__projected_fields__:
                domain[cls.__tablename__]['datasource']['projection'].update(
                    {field: 1}
                )

            domain[cls.__tablename__]['public_methods'] \
                = cls.__public_methods__

            """ Users should not provide _author fields """
            del domain[cls.__tablename__]['schema']['_author']

    """ Make it possible to retrive a user with his username (/users/name) """
    domain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'username',
        }
    })

    """ Hide passwords """

    domain['users']['datasource']['projection']['password'] = 0

    """ Only accept email addresses for email fields """
# FIXME(Conrad): There could be a generic way to add regexes to fields in the
#                model
    domain['users']['schema']['email'].update(
        {'regex': config['EMAIL_REGEX']})
    domain['forwardaddresses']['schema']['address'].update(
        {'regex': config['EMAIL_REGEX']})
    domain['eventsignups']['schema']['email'].update(
        {'regex': config['EMAIL_REGEX']})

    """ Only allow existing roles for new permissions """
    domain['permissions']['schema']['role'].update(
        {'allowed': permission_matrix.roles.keys()})

    """Workaround to signal onInsert that this request is internal"""
    domain['eventsignups']['schema'].update({
        '_confirmed': {
            'type': 'boolean',
            'required': False,
        },
    })
    domain['forwardaddresses']['schema'].update({
        '_confirmed': {
            'type': 'boolean',
            'required': False,
        }
    })

    domain[models.Session.__tablename__]['resource_methods'] = ['GET']

    """
    HERE BEGIN SMALL DEFINITIONS FOR SOME RESSOURCES
    """

    """time_end for /events requires time_start"""
    domain['events']['schema']['time_end'].update({
        'dependencies': ['time_start']
    })

    """Maybe this can be automated through the model somehow"""
    domain['events']['schema'].update({
        'img_thumbnail': {'type': 'media'},
        'img_web': {'type': 'media'},
        'img_1920_1080': {'type': 'media'}
    })

    domain['files']['schema'].update({
        'data': {'type': 'media', 'required': True}
    })

    domain['joboffers']['schema'].update({
        'logo': {'type': 'media'},
        'pdf': {'type': 'media'}
    })
