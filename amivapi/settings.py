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

# Flask

DEBUG = False
TESTING = False

# Eve

# AUTH_FIELD = "_author"  # TODO(Alex): If we enable oplog, do we need this?
DOMAIN = {}  # Empty add first, resource will be added in bootstrap
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
EMAIL_REGEX = '^.+@.+$'
BANDWIDTH_SAVER = False
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']
XML = False
X_DOMAINS = '*'
X_HEADERS = ['Authorization', 'If-Match', 'Content-Type']
RETURN_MEDIA_AS_BASE64_STRING = False
EXTENDED_MEDIA_INFO = ['filename', 'size', 'content_url']

# Amivapi

PASSWORD_CONTEXT = CryptContext(
    schemes=["pbkdf2_sha256"],

    # default_rounds is used when hashing new passwords, to be varied each
    # time by vary_rounds
    pbkdf2_sha256__default_rounds=10 ** 5,
    pbkdf2_sha256__vary_rounds=0.1,

    # min_rounds is used to determine if a hash needs to be upgraded
    pbkdf2_sha256__min_rounds=8 * 10 ** 4,
)

SESSION_TIMEOUT = timedelta(days=365)

# Default root password
ROOT_PASSWORD = u"root"  # Will be overwridden by config.py

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
