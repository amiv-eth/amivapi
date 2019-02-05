# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Summarize unique keys to facilitate further studydoc filtering."""

import json

from werkzeug.exceptions import HTTPException
from flask import current_app, request
from eve.utils import parse_request
from eve.io.mongo.parser import parse


def add_summary(response):
    """Add summary to response."""
    # Get the where clause to return summary only for matching documents
    lookup = _get_lookup()

    # Compute distinct values per field (remove fields without any values)
    summary = {fieldname: _count_distinct(lookup, fieldname)
               for fieldname in _summary_fields()}
    response['_summary'] = {k: v for k, v in summary.items() if v}


def _summary_fields():
    return [
        fieldname for fieldname, schema
        in current_app.config['DOMAIN']['studydocuments']['schema'].items()
        if schema.get('allow_summary')
    ]


def _count_distinct(lookup, fieldname):
    """Use mongodb aggregation to count distinct values."""
    aggregation = current_app.data.driver.db['studydocuments'].aggregate([
        {'$match': lookup},
        {'$group': {'_id': '$' + fieldname, '_count': {'$sum': 1}}},
    ])
    return {item['_id']: item['_count'] for item in aggregation
            if item['_id'] is not None}


def _get_lookup():
    """Get the where clause lookup just like Eve does.

    Unfortunately, Eve only parses the `where` at a very low level and does not
    provide any methods to elegantly access it, so we have use the same
    internal functions as Eve does.
    (Recently, Eve has at least somewhat exposed the parsing, but this
    code is not part of an official release yet [1])

    As soon as there is some 'official' support, this can be removed,
    as it is basically copied, with the abort removed for simplicity
    (as Eve itself will already abort if there's an error).

    [1]: https://github.com/pyeve/eve/blob/master/eve/io/mongo/mongo.py
    """
    req = parse_request('studydocuments')
    if req and req.where:
        try:
            # Mongo Syntax
            return current_app.data._sanitize(json.loads(req.where))
        except (HTTPException, json.JSONDecodeError):
            # Python Syntax
            return parse(req.where)

    return {}  # No where clause
