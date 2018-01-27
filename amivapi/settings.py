# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Default settings for all environments.

These settings will be extended by additional config files in ROOT/config.
Run `python manage.py create_config` to create such a config file.
"""

from datetime import timedelta

from passlib.context import CryptContext

VERSION = '0.9dev'

# Default user config

# Flask

DEBUG = False
TESTING = False

# Eve & Amivapi

# AUTH_FIELD = "_author"  # TODO(Alex): If we enable oplog, do we need this?
DOMAIN = {}  # Empty add first, resource will be added in bootstrap
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
EMAIL_REGEX = '^.+@.+$'
BANDWIDTH_SAVER = False
AUTO_COLLAPSE_MULTI_KEYS = True
AUTO_CREATE_LISTS = True
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']
XML = False
X_DOMAINS = '*'
X_HEADERS = ['Authorization', 'Content-Type', 'Cache-Control',
             'If-Match', 'If-None-Match', 'If-Modified-Since']
MONGO_QUERY_BLACKLIST = ['$where']  # default blacklists where and regex queries
CACHE_CONTROL = 'no-store, must-revalidate'

# MongoDB
MONGO_DBNAME = 'amivapi'
MONGO_HOST = 'localhost'
MONGO_PASSWORD = ''
MONGO_PORT = 27017
MONGO_USERNAME = ''

# File Storage
RETURN_MEDIA_AS_BASE64_STRING = False
RETURN_MEDIA_AS_URL = True
MEDIA_URL = 'string'  # Very important to match url properly
EXTENDED_MEDIA_INFO = ['name', 'content_type', 'length', 'upload_date']

# Mailing Lists
MAILING_LIST_DIR = ''  # By default, no forwards are saved
MAILING_LIST_FILE_PREFIX = '.forward+'

# SMTP server defaults
API_MAIL = 'api@amiv.ethz.ch'
SMTP_HOST = 'localhost'
SMTP_PORT = 587
SMTP_TIMEOUT = 10

# LDAP
ENABLE_LDAP = False
LDAP_USER = ''
LDAP_PASS = ''

# Security
ROOT_PASSWORD = u"root"  # Will be overwridden by config.py
SESSION_TIMEOUT = timedelta(days=365)
PASSWORD_CONTEXT = CryptContext(
    schemes=["pbkdf2_sha256"],

    # default_rounds is used when hashing new passwords, to be varied each
    # time by vary_rounds
    pbkdf2_sha256__default_rounds=10 ** 3,
    pbkdf2_sha256__vary_rounds=0.1,

    # min_rounds is used to determine if a hash needs to be upgraded
    pbkdf2_sha256__min_rounds=8 * 10 ** 2,
)

# Email sent to external users signing up for events
CONFIRM_EMAIL_TEXT = (
    "Hello from AMIV!\n\nYou have signed up for %(title)s with your E-Mail "
    "address. To verify this is a valid address and keep your spot please click"
    " this link: %(link)s\n\nBest regards,\nAMIV!"
)

# Signup confirmation without redirct
CONFIRM_TEXT = "Your singup was confirmed!"
SIGNUP_DELETED_TEXT = "Your signup was removed."

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

# All departments at ETH
DEPARTMENT_LIST = [
    'itet',
    'mavt',
    'arch',
    'baug',
    'bsse',
    'infk',
    'matl',
    'biol',
    'chab',
    'math',
    'phys',
    'erdw',
    'usys',
    'hest',
    'mtec',
    'gess'
]

# Config for swagger (/docs)
# TODO: should be linked to the setup.py information in the package
SWAGGER_INFO = {
    'title': 'AMIVAPI Documentation',
    'version': VERSION,
    'description': "The REST API behind most of AMIV's web services.",
    # TODO: fill this
    'termsOfService': 'todo',
    'contact': {
        'name': 'AMIV an der ETH',
        'url': 'https://amiv.ch/'
    },
    'license': {
        'name': 'GNU Affero General Public License',
        'url': 'https://github.com/amiv-eth/amivapi/blob/master/LICENSE',
    }
}
ENABLE_HOOK_DESCRIPTION = True
HIDE_HOOK_FUNCTIONS = ['authenticate',
                       'check_if_admin',
                       'abort_if_not_public',
                       'add_lookup_filter',
                       'check_resource_write_permission',
                       'check_item_write_permission',
                       'add_permitted_methods_after_insert',
                       'add_permitted_methods_after_fetch_resource',
                       'add_permitted_methods_after_fetch_item',
                       'add_permitted_methods_after_fetch_resource',
                       'add_permitted_methods_for_home',
                       'add_permitted_methods_after_update']
