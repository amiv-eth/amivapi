# -*- coding: utf-8 -*-
#
# AMIVAPI localization.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import request, current_app as app
from eve.methods.post import post_internal
from eve.utils import config
from amivapi.models import Translation


def insert_localized_fields(response):
    """Insert title and description field into event and joboffer with correct
    language
    This is done like this and not more abstract since there are only four
    localized fields in total
    """
    for field in ['title', 'description']:
        id = response['%s_id' % field]

        session = app.data.driver.session

        query = session.query(
            Translation.language, Translation.content
        ).filter_by(localization_id=id)

        locales = {}

        for language, content in query:
            locales[language] = content

        match = request.accept_languages.best_match(locales.keys())

        if match:
            response[field] = locales[match]
        else:
            default = config.DEFAULT_LANGUAGE
            if default in locales.keys():  # Try to fall back to default
                response[field] = locales[default]
            else:
                response[field] = u''  # Last resort: Just empty field


def create_localization_ids(items):
    """Whenever a event or joboffer is created, add translation fields"""
    for item in items:
        mapping = post_internal("translationmappings", payl={})
        item['title_id'] = mapping[0]['id']
        mapping = post_internal("translationmappings", payl={})
        item['description_id'] = mapping[0]['id']
