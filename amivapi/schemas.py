from amivapi import models
from eve.io.sql.decorators import registerSchema
from inspect import getmembers, isclass


def load_domain(config):
    for cls_name, cls in getmembers(models):
        if(isclass(cls)
                and cls.__module__ == "amivapi.models"
                and cls.__expose__ == True):
            registerSchema(cls.__tablename__)(cls)


    domain = config['DOMAIN'] = {}
    for obj_name in dir(models):
        obj = getattr(models, obj_name)
        if hasattr(obj, "_eve_schema"):
            domain.update(obj._eve_schema)

    """ Definition of additional projected fields """
    domain['users']['datasource']['projection'].update({
        'groups': 1
    })
    domain['groups']['datasource']['projection'].update({
        'members': 1
    })
    domain['forwards']['datasource']['projection'].update({
        'user_subscribers': 1,
        'address_subscribers': 1
    })
    domain['forwardusers']['datasource']['projection'].update({
        'forward': 1,
        'user': 1
    })
    domain['forwardaddresss']['datasource']['projection'].update({
        'forward': 1
    })
    domain['sessions']['datasource']['projection'].update({
        'user': 1
    })
    domain['events']['datasource']['projection'].update({
        'signups': 1
    })
    domain['eventsignups']['datasource']['projection'].update({
        'event': 1,
        'user': 1
    })
    domain['studydocuments']['datasource']['projection'].update({
        'files': 1
    })

    """ Make it possible to retrive a user with his username (/users/name) """
    domain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'username',
        }
    })

    # domain['groupmemberships']['resource_methods'] = ['GET']
    domain['groupmemberships']['schema']['group_id']['data_relation']['resource'] = 'groups'
    domain['groupmemberships']['schema']['user_id']['data_relation']['resource'] = 'users'
