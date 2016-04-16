# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import warnings
import random
from tempfile import NamedTemporaryFile, mkdtemp
from os import unlink, rmdir

from amivapi import bootstrap, utils


#engine = None
#connection = None

# Config overwrites
test_config = {
    'MONGO_DBTEST': 'test_amivapi',
    'STORAGE_DIR': '',
    'FORWARD_DIR': '',
    'ROOT_MAIL': 'nobody@example.com',
    'SMTP_SERVER': '',
    'APIKEYS': {},
    'TESTING': True,
    'DEBUG': False
}
