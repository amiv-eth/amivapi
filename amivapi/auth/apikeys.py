# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Authorization with apikeys.

Provides the apikey resource and hooks to handle authorization with a key.

API keys should only be created or modified by admins.
"""
from datetime import datetime as dt, timezone

from flask import abort, current_app, g

from amivapi.auth.auth import AdminOnlyAuth
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
        new_time = dt.now(timezone.utc).replace(microsecond=0)
        apikeys.update_one({'_id': apikey['_id']},
                           {'$set': {'_updated': new_time}})

        if permission == 'read':
            g.resource_admin_readonly = True
        elif permission == 'readwrite':
            g.resource_admin = True
        elif g.get('auth_required'):
            abort(403, "The API key exists but does not grant the required "
                       "permissions.")


description = ("""
API keys can be used to give permissions to other applications.

When creating an API key, permissions have to be provided as an object with
the resources as keys and the respective permissions as values, e.g.

```
{
    "users": "read",
    "sessions": "readwrite"
}
```

(this would grant the API key rights to see all users and see
and modify/delete all sessions).

> **IMPORTANT: The most powerful permission**
>
> If you grant an API key `readwrite` permissions to API keys, this key will
> be able to create new API keys with any permissions and also modify it's
> own permissions!
>
> As a result, **`readwrite` permissions for api keys should only be assigned
> with great care**!

Just like [sessions](#tag/Session), API keys return a token which can be
sent in the header
[as described above](#section/Authentication-and-Authorization).
""")


apikeydomain = {
    'apikeys': {
        'resource_title': 'API Keys',
        'item_title': 'API Key',

        'description': description,

        'public_methods': [],
        'public_item_methods': [],
        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': AdminOnlyAuth,

        'schema': {
            'name': {
                'description': 'A unique name to identify the key.',
                'example': 'Beer Machine',

                'type': 'string',
                'required': True,
                'nullable': False,
                'empty': False,
                'unique': True
            },
            'token': {
                'type': 'string',
                'readonly': True,
                'description': 'The token that can be used for auth. '
                               'Will be randomly generated for every new key.',
                'example': 'Xfh3abXzLoezpwO9WT7oRw',
            },
            'permissions': {
                'description': 'The permissions the API key grants. The value '
                               'is an object with resources as keys and the '
                               'permissions as a values.',
                'example': {
                    'users': 'read',
                    'beverages': 'readwrite',
                },

                'type': 'dict',
                'keyschema': {'type': 'string',
                              'api_resources': True},
                'valuesrules': {'type': 'string',
                                'allowed': ['read', 'readwrite']},
                'required': True,
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
