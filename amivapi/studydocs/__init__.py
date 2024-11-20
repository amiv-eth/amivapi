# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event module.

Contains settings for eve resource, special validation and email_confirmation
logic needed for signup of non members to events.
"""
from amivapi.studydocs.authorization import add_uploader_on_insert
from amivapi.studydocs.summary import add_summary
from amivapi.studydocs.rating import (
    init_rating, update_rating_post, update_rating_patch, update_rating_delete)
from amivapi.studydocs.model import studydocdomain, StudyDocValidator
from amivapi.utils import register_domain, register_validator


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, studydocdomain)
    register_validator(app, StudyDocValidator)

    # Uploader
    app.on_insert_studydocuments += add_uploader_on_insert

    # Rating
    app.on_insert_studydocuments += init_rating
    app.on_inserted_studydocumentratings += update_rating_post
    app.on_updated_studydocumentratings += update_rating_patch
    app.on_deleted_item_studydocumentratings += update_rating_delete

    # Meta summary
    app.on_fetched_resource_studydocuments += add_summary
