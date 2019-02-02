# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Summarize unique keys to facilitate further studydoc filtering."""

from flask import g, current_app


def save_lookup(request, lookup):
    """Save the current lookup in the requests globals if summary is requested.

    We can only modify the response later, when we don't have easy access
    to the lookup anymore (but we need it to filter the summary).

    TODO(Alex): `lookup` is only the path parsed by flask, and does not include
                the `where` query. How to get the actual filter from Eve?
    """
    if True:
        g.saved_lookup = lookup
    else:
        g.saved_lookup = None


def add_summary(response):
    """Add summary to response, if requested."""
    lookup = g.saved_lookup
    if lookup is None:
        return

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
