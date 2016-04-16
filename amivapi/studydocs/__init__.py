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

from .endpoints import make_studydocdomain


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_studydocdomain())
