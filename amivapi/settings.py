"""Default settings for all environments.

These settings will be extended by additional config files in ROOT/config.
Run `python manage.py create_config` to create such a config file.
"""

from os.path import abspath, dirname, join
from datetime import timedelta

# Custom
ROOT_DIR = abspath(join(dirname(__file__), ".."))

# Flask
DEBUG = False
TESTING = False

# Flask-SQLALchemy

# Eve
ID_FIELD = "id"
AUTH_FIELD = "_author"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
BANDWIDTH_SAVER = False
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']
PUBLIC_METHODS = ['GET']  # This is the only way to make / public
XML = False

# Eve, file storage options
RETURN_MEDIA_AS_BASE64_STRING = False
EXTENDED_MEDIA_INFO = ['filename', 'size', 'content_url']
STORAGE_URL = r'/storage'  # Not eve yet, atm our own implementation

# Custom Default language
DEFAULT_LANGUAGE = 'de'
SESSION_TIMEOUT = timedelta(days=365)

""" This is a list of which groups exist to grant permissions. It should be
possible to change anything without breaking stuff. """

ROLES = {
    'vorstand': {
        'users': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1,
        },
        'permissions': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwards': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardusers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        '_forwardaddresses': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'sessions': {
            'GET': 1,
            'DELETE': 1
        },
        'events': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        '_eventsignups': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'files': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'studydocuments': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'joboffers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'read-everything': {
        'users': {
            'GET': 1,
        },
        'permissions': {
            'GET': 1,
        },
        'forwards': {
            'GET': 1,
        },
        'forwardusers': {
            'GET': 1,
        },
        '_forwardaddresses': {
            'GET': 1,
        },
        'sessions': {
            'GET': 1,
        },
        'events': {
            'GET': 1,
        },
        '_eventsignups': {
            'GET': 1,
        },
        'files': {
            'GET': 1,
        },
        'studydocuments': {
            'GET': 1,
        },
        'joboffers': {
            'GET': 1,
        }
    },
    'event-admin': {
        'events': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        '_eventsignups': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'job-admin': {
        'files': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'joboffers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'mail-admin': {
        'forwards': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardusers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        '_forwardaddresses': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'studydocs-admin': {
        'files': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'studydocuments': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    }
}
