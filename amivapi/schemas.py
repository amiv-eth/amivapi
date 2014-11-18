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

    config['EMBEDDING'] = True
    domain['users']['embedding'] = True

    domain['groupmemberships']['resource_methods'] = ['GET']

    """ Make it possible to retrive a user with his username (/users/name) """
    domain['users'].update({
        'additional_lookup': {
            'url': 'regex(".*[\w].*")',
            'field': 'username',
        }
    })
