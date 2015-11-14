# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Default settings for all environments.

These settings will be extended by additional config files in ROOT/config.
Run `python manage.py create_config` to create such a config file.
"""

from os.path import abspath, dirname, join
from datetime import timedelta

from passlib.context import CryptContext


# Custom
ROOT_DIR = abspath(join(dirname(__file__), ".."))

PASSWORD_CONTEXT = CryptContext(
    schemes=["pbkdf2_sha256"],

    # default_rounds is used when hashing new passwords, to be varied each
    # time by vary_rounds
    pbkdf2_sha256__default_rounds=10**5,
    pbkdf2_sha256__vary_rounds=0.1,

    # min_rounds is used to determine if a hash needs to be upgraded
    pbkdf2_sha256__min_rounds=8 * 10**4,
)

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
X_DOMAINS = '*'
X_HEADERS = ['Authorization', 'If-Match']

# Eve, file storage options
RETURN_MEDIA_AS_BASE64_STRING = False
EXTENDED_MEDIA_INFO = ['filename', 'size', 'content_url']

# Custom Default language
DEFAULT_LANGUAGE = 'de'
SESSION_TIMEOUT = timedelta(days=365)

# Text for automatically sent mails

# First argument is role name
PERMISSION_EXPIRED_WARNMAIL_SUBJECT = (
    "Your permissions as %(role)s at AMIV are about to expire")
# First argument is name, second role, third admin email
PERMISSION_EXPIRED_WARNMAIL_TEXT = (
    "Hello %(name)s,\nYour permissions as %(role)s at AMIV will expire in 14 "
    "days. If you want to get them renewed please sent an E-Mail to "
    " %(admin_mail)s.\n\nRegards\n\nAutomatically sent by AMIV API"
)

# All organisational units (ou) in ldap which are assigned to AMIV (by VSETH)
LDAP_MEMBER_OU_LIST = [
    u'Biomedical Engineering MSc',
    u'Dr. Informationstechnologie und Elektrotechnik',
    u'Dr. Maschinenbau und Verfahrenstechnik',
    u'DZ Elektrotechnik und Informationstechnologie',
    u'DZ Maschineningenieurwiss. und Verfahrenstechnik',
    u'Elektrotech. und Informationstechnol. (Mobilität)',
    u'Elektrotechnik und Informationstechnologie BSc',
    u'Elektrotechnik und Informationstechnologie MSc',
    u'Energy Science and Technology MSc',
    u'Informationstechnologie und Elektrotechnik',
    u'Maschinenbau und Verfahrenstechnik',
    u'Maschineningenieurwissenschaften (Mobilität)',
    u'Maschineningenieurwissenschaften BSc',
    u'Maschineningenieurwissenschaften MSc',
    u'Micro- and Nanosystems MSc',
    u'Nuclear Engineering MSc',
    u'Nuclear Engineering MSc (EPFL)',
    u'Robotics, Systems and Control MSc',
    u'Verfahrenstechnik MSc',
    u'Doktorat Informationstechnologie & Elektrotechnik',
    u'Doktorat Maschinenbau und Verfahrenstechnik'
]

# This is a list of which groups exist to grant permissions. It should be
# possible to change anything without breaking stuff.
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
        'groups': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardaddresses': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'groupusermembers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'groupaddressmembers': {
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
        'eventsignups': {
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
        'groups': {
            'GET': 1,
        },
        'forwardaddresses': {
            'GET': 1,
        },
        'groupusermembers': {
            'GET': 1,
        },
        'groupaddressmembers': {
            'GET': 1,
        },
        'sessions': {
            'GET': 1,
        },
        'events': {
            'GET': 1,
        },
        'eventsignups': {
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
        'eventsignups': {
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
        'groups': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardaddresses': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'groupusermembers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'groupaddressmembers': {
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
