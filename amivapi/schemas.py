from amivapi import models

def load_domain(config):
    domain = config['DOMAIN'] = {}
    for obj_name in dir(models):
        obj = getattr(models, obj_name)
        if hasattr(obj, "_eve_schema"):
            domain.update(obj._eve_schema)

    config['EMBEDDING'] = True
    domain['users']['embedding'] = True

