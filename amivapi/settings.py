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

VERSION = '1.1.0'

# Sentry

SENTRY_DSN = None
SENTRY_ENVIRONMENT = None

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
MERGE_NESTED_DOCUMENTS = False
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']
RENDERERS = ['eve.render.JSONRenderer']
X_DOMAINS = '*'
X_HEADERS = ['Authorization', 'Content-Type', 'Cache-Control',
             'If-Match', 'If-None-Match', 'If-Modified-Since']
MONGO_QUERY_BLACKLIST = ['$where']  # default blacklists where and regex queries
CACHE_CONTROL = 'no-store, must-revalidate'

# MongoDB
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DBNAME = 'amivapi'
MONGO_USERNAME = 'amivapi'
MONGO_PASSWORD = 'amivapi'

# File Storage
RETURN_MEDIA_AS_BASE64_STRING = False
RETURN_MEDIA_AS_URL = True
MEDIA_URL = 'string'  # Very important to match url properly
EXTENDED_MEDIA_INFO = ['name', 'content_type', 'length', 'upload_date']

# Mailing Lists, local and remote options (by default no storage)
MAILING_LIST_FILE_PREFIX = '.forward+'  # default file name: .forward+groupname
MAILING_LIST_DIR = None
REMOTE_MAILING_LIST_ADDRESS = None
REMOTE_MAILING_LIST_KEYFILE = None
REMOTE_MAILING_LIST_DIR = './'  # Use home directory on remote by default

# SMTP server defaults
API_MAIL = 'api@amiv.ethz.ch'
SMTP_HOST = 'localhost'
SMTP_PORT = 587
SMTP_TIMEOUT = 10

# LDAP
LDAP_USERNAME = None
LDAP_PASSWORD = None

# Execution of periodic tasks with `amivapi run cron`
CRON_INTERVAL = timedelta(minutes=5)  # per default, check tasks every 5 min

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

# Newsletter subscriber list view authorization
SUBSCRIBER_LIST_USERNAME = None
SUBSCRIBER_LIST_PASSWORD = None

# Aspect ratio validator error tolerance in percent (e.g. 0.025 <=> 2.5%)
ASPECT_RATIO_TOLERANCE = 0.025

# OAuth

# See https://tools.ietf.org/html/rfc6749#section-3.1.2
# The redirect URL must be absolute, may include query params and must not
# include a fragment.
# We also require https, because we do not want to send tokens over
# unencrypted connections.
# An expection to this is `localhost`, which can be registered without
# https to allow testing of local tools (if required)
REDIRECT_URI_REGEX = '^((http://)?localhost[^#]*|https://[^#]+)$'

# Email sent to external users signing up for events
CONFIRM_EMAIL_TEXT = (
    "Hello from AMIV!\n\nYou have signed up for %(title)s with your E-Mail "
    "address. To verify this is a valid address and keep your spot please click"
    " this link: %(link)s\n\nBest regards,\nAMIV!"
)

# Signup confirmation without redirct
CONFIRM_TEXT = "Your singup was confirmed!"
SIGNUP_DELETED_TEXT = "Your signup was removed."


# In LDAP, the 'departmentNumber' field contains the students departments
# It contains: type of person, e.g. student, department, exact field of study
# We can use this to discover department of students
LDAP_DEPARTMENT_MAP = {
    # (phrase in departmentNumber for our members): department of member
    u'ETH Student D-ITET': u'itet',  # for BSc, MSc as well as PhD students!
    u'ETH Studentin D-ITET': u'itet',
    u'ETH Student D-MAVT': u'mavt',
    u'ETH Studentin D-MAVT': u'mavt',
    # All other departments are mapped to 'None' (s.t. None equals 'no member')
}


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

LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     viewbox="0 0 156.526 48.046">
  <defs><path id="a" d="M0 0h196.052v84.956H0z"/></defs>
  <clipPath id="b">
    <use xlink:href="#a"
      overflow="visible"
      width="100%"
      height="100%"/>
  </clipPath>
  <path clip-path="url(#b)"
    d="M89.187 46.405h-5.19c-2.369 0-3.679 1.109-3.679 2.975 0 1.813 1.21 3.022
    3.78 3.022 1.814 0 2.973-.15 4.132-1.26.706-.655.957-1.713.957-3.326zm.151
    11.088v-2.269c-1.764 1.764-3.427 2.521-6.45 2.521-2.974
    0-5.141-.757-6.703-2.318-1.411-1.462-2.167-3.578-2.167-5.896
    0-4.183 2.872-7.609
    8.97-7.609h6.198v-1.31c0-2.872-1.41-4.132-4.888-4.132-2.519
    0-3.678.605-5.039 2.167l-4.182-4.082c2.569-2.822 5.089-3.628 9.473-3.628
    7.358 0 11.188 3.124 11.188 9.272v17.286h-6.4zm41.892
    0V41.619c0-3.578-2.269-4.787-4.334-4.787-2.017 0-4.384 1.209-4.384
    4.636v16.025h-6.553V41.619c0-3.578-2.267-4.787-4.333-4.787-2.065 0-4.385
    1.209-4.385 4.787v15.875h-6.551V31.238h6.399v2.419c1.715-1.764 4.133-2.721
    6.552-2.721 2.923 0 5.291 1.058 6.955 3.326 2.217-2.319 4.586-3.326
    7.86-3.326 2.62 0 4.989.856 6.45 2.318 2.117 2.116 2.873 4.586 2.873
    7.458v16.781zm11.503-26.255h6.551v26.255h-6.551zm27.964 0l-5.291
    16.227-5.341-16.227h-6.904l9.675 26.255h5.141l9.625-26.253v-.002zM69.703
    45.854a24.72 24.72 0 0 0
    .221-3.251c0-1.103-.08-2.186-.221-3.251l-5.747-.892a19.025 19.025 0 0
    0-1.086-3.357l4.121-4.096a24.648 24.648 0 0 0-1.731-2.76 24.656 24.656 0 0
    0-2.09-2.5l-5.168 2.652a19.068 19.068 0 0
    0-1.373-1.102c-.484-.351-.98-.673-1.484-.972l.926-5.735a24.496 24.496 0 0
    0-3.024-1.216 24.705 24.705 0 0 0-3.159-.794l-2.626 5.192a19.073 19.073 0 0
    0-3.52.007l-2.629-5.199a24.72 24.72 0 0 0-3.16.794 24.699 24.699 0 0
    0-3.023 1.215l.927 5.743a18.806 18.806 0 0 0-2.851
    2.071l-5.175-2.656a24.546 24.546 0 0 0-2.09 2.5 24.513 24.513 0 0 0-1.732
    2.76l4.126 4.101a18.667 18.667 0 0 0-1.089 3.351l-5.748.893a24.55 24.55 0 0
    0-.222 3.251c0 1.103.08 2.186.222 3.251l5.756.894a18.996 18.996 0 0 0 1.082
    3.35L24.009 54.2a24.513 24.513 0 0 0 1.732 2.76 24.31 24.31 0 0 0 2.09
    2.5l5.168-2.652c.441.387.9.759 1.384 1.11.48.349.972.669 1.472.966l-.926
    5.733c.969.464 1.975.875 3.024 1.216 1.049.342 2.104.6
    3.16.793l2.622-5.185c1.177.109 2.357.106 3.528-.004l2.624 5.189a24.35 24.35
    0 0 0 3.16-.794 24.713 24.713 0 0 0 3.024-1.215l-.925-5.729a18.882 18.882 0
    0 0 2.862-2.079l5.162 2.649a24.568 24.568 0 0 0 2.09-2.5 24.558 24.558 0 0
    0 1.731-2.76l-4.115-4.091a18.839 18.839 0 0 0 1.093-3.364zm-36.652
    2.467c-1.989-4.355-1.65-9.632 1.36-13.775 4.445-6.118 13.038-7.479
    19.156-3.034.435.316.839.658 1.225 1.013l-4.176 3.034-4.056-5.582-4.473
    3.25 4.056 5.583-.007.005-12.772 1.245 3.82 5.258zm23.55 2.347c-4.445
    6.118-13.038 7.479-19.156 3.034a13.892 13.892 0 0 1-1.129-.918l4.119-2.992
    4.095 5.638 5.135-11.771 3.768 5.186 4.473-3.25-4.039-5.56
    4.147-3.013c1.926 4.331 1.568 9.542-1.413 13.646"
    transform="translate(-21.076 -18.58)" fill="#e8462b"/>
</svg>
"""
