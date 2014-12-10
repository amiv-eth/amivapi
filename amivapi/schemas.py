from amivapi import models
from eve.io.sql.decorators import registerSchema
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

    """ Make it possible to retrive a user with his username (/users/name) """
    domain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'username',
        }
    })

    """need to confirm this workaround"""
    domain['eventsignups']['schema'].update({
        '_confirmed': {
            'type': 'boolean',
            'required': False,
        },
    })
