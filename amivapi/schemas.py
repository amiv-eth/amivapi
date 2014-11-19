from amivapi import models
from eve.io.sql.decorators import registerSchema

registerSchema('users')(models.User)
registerSchema('groups')(models.Group)
registerSchema('groupmemberships')(models.GroupMembership)
registerSchema('forwards')(models.Forward)
registerSchema('forwardusers')(models.ForwardUser)
registerSchema('forwardaddresses')(models.ForwardAddress)
registerSchema('sessions')(models.Session)
registerSchema('events')(models.Event)
registerSchema('signups')(models.EventSignup)
registerSchema('files')(models.File)
registerSchema('studydocuments')(models.StudyDocument)
registerSchema('joboffers')(models.JobOffer)


def load_domain(config):
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
    domain['forwardaddresses']['datasource']['projection'].update({
        'forward': 1
    })
    domain['sessions']['datasource']['projection'].update({
        'user': 1
    })
    domain['events']['datasource']['projection'].update({
        'signups': 1
    })
    domain['signups']['datasource']['projection'].update({
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
