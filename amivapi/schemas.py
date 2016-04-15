# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.


def get_domain():
    domain = {}

    # Add entry for storage so auth can find it

    domain['storage'] = {
        'resource_methods': ['GET'],
        'item_methods': ['GET'],
        'public_methods': [],
        'public_item_methods': [],
        'registered_methods': ['GET'],
        'description': {
            'general': 'Endpoint to download files, get the URLs via /files'
        }
    }

    return domain
