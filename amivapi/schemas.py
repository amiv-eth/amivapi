from amivapi import models, permission_matrix
from eve.io.sql.decorators import registerSchema
from inspect import getmembers, isclass
from amivapi.confirm import documentation as confirm_documentation


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

            # For documentation
            domain[cls.__tablename__]['description'] \
                = cls.__description__

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
    domain['_forwardaddresses']['schema']['address'].update(
        {'regex': config['EMAIL_REGEX']})
    domain['_eventsignups']['schema']['email'].update(
        {'regex': config['EMAIL_REGEX']})

    """ Only allow existing roles for new permissions """
    domain['permissions']['schema']['role'].update(
        {'allowed': permission_matrix.roles.keys()})

    """Workaround to signal onInsert that this request is internal"""
    domain['_eventsignups']['schema'].update({
        '_confirmed': {
            'type': 'boolean',
            'required': False,
        },
    })
    domain['_forwardaddresses']['schema'].update({
        '_confirmed': {
            'type': 'boolean',
            'required': False,
        }
    })

    """internal resources should not be accessed from outside"""
    domain['_eventsignups']['internal_resource'] = True
    domain['_forwardaddresses']['internal_resource'] = True

    domain[models.Session.__tablename__]['resource_methods'] = ['GET']

    """No Patching for files, only replacing"""
    domain[models.File.__tablename__]['item_methods'] = ['GET', 'PUT',
                                                         'DELETE']

    """time_end for /events requires time_start"""
    domain['events']['schema']['time_end'].update({
        'dependencies': ['time_start']
    })

    """enums of sqlalchemy should directly be catched by the validator"""
    domain['users']['schema']['gender'].update({
        'allowed': ['male', 'female']
    })
    domain['users']['schema']['department'].update({
        'allowed': ['itet', 'mavt']
    })

    """
    Filetype needs to be specified as media, maybe this can be automated
    """
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
        'pdf': {'type': 'media'},
        'title': {'type': 'dict'}
    })

    """
    Locatization-revelant: Hide the mapping table
    Remove title and description id from events and joboffers schema so they
    can not be set manually
    """
    domain['translationmappings']['internal_resource'] = True
    del domain['joboffers']['schema']['title_id']
    del domain['joboffers']['schema']['description_id']
    del domain['events']['schema']['title_id']
    del domain['events']['schema']['description_id']

    """add the documentation of the blueprints to a custom config-Field"""
    print_docu = config['BLUEPRINT_DOCUMENTATION'] = {}
    print_docu.update(confirm_documentation)
