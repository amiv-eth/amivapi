# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Authorization with apikeys.

Provides the apikey resource and hooks to handle authorization with a key.

API keys should only be created or modified by admins.
"""
from datetime import datetime as dt

from flask import abort, current_app, g

from amivapi.auth.auth import AmivTokenAuth
from amivapi.utils import register_domain

try:
    from secrets import token_urlsafe
except ImportError:
    # Fallback for python3.5
    from amivapi.utils import token_urlsafe


def authorize_apikeys(resource):
    """Check if user is an apikey, and if it is, do authorization.

    Also update 'updated' timestamp everytime a key is accessed
    """
    apikeys = current_app.data.driver.db['apikeys']
    apikey = apikeys.find_one({'token': g.get('current_token')},
                              {'permissions': 1})

    if apikey:
        # Get permission for resource if they exist
        permission = apikey['permissions'].get(resource)

        # Update timestamp (remove microseconds to match mongo precision)
        new_time = dt.utcnow().replace(microsecond=0)
        apikeys.update_one({'_id': apikey['_id']},
                           {'$set': {'_updated': new_time}})

        if permission == 'read':
            g.resource_admin_readonly = True
        elif permission == 'readwrite':
            g.resource_admin = True
        elif g.get('auth_required'):
            abort(403, "The API key exists but does not grant the required "
                       "permissions.")


class ApikeyAuth(AmivTokenAuth):
    """Do not let (non-admin) users view API keys at all.

    If this hook gets called, the user is not an admin for this resource.
    Therefore no results should be given. To give a more precise error message,
    we abort. Otherwise normal users would just see an empty list."""
    def create_user_lookup_filter(self, user):
        abort(403)


apikeydomain = {
    'apikeys': {
        'description': "API Keys can be used to given permissions to other "
                       "applications.",

        'public_methods': [],
        'public_item_methods': [],
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': ApikeyAuth,

        'schema': {
            'name': {
                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'description': 'A name to identify the key.',
                'unique': True
            },
            'token': {
                'type': 'string',
                'readonly': True,
                'description': 'The token that can be used for auth. '
                'Will be randomly generated for every new key.'
            },
            'permissions': {
                'type': 'dict',
                'propertyschema': {'type': 'string',
                                   'api_resources': True},
                'valueschema': {'type': 'string',
                                'allowed': ['read', 'readwrite']},
                'description': 'Permissions the apikey grants. '
                'Key, value pairs with resource names as keys and either '
                '"read" or "readwrite" as values.'
            }
        },
    }
}


def generate_tokens(items):
    for item in items:
        item['token'] = token_urlsafe()


def init_apikeys(app):
    """Register API Key resource and add auth hook."""
    register_domain(app, apikeydomain)
    app.after_auth += authorize_apikeys
    app.on_insert_apikeys += generate_tokens
