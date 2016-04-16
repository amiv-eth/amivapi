# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.events.email_confirmations import documentation


def get_blueprint_doc():
    ret = {}
    ret.update(documentation)
    return ret
