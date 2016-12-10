# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event module.

Contains settings for eve resource, special validation and email_confirmation
logic needed for signup of non members to events.
"""

from amivapi.utils import register_domain

from .model import studydocdomain
from .authorization import add_uploader_on_insert, add_uploader_on_bulk_insert


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, studydocdomain)

    app.on_insert_item_studydocuments += add_uploader_on_insert
    app.on_insert_studydocuments += add_uploader_on_bulk_insert
