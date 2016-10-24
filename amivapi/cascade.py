# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Delete cascading system.

This adds an option 'cascade_delete' to data_relations in the schema. If it is
set to true, then deleting the referenced object will also delete the
referencing object. If false, the reference will be set to NULL, when the
referenced object is deleted.
"""

from flask import current_app
from werkzeug.exceptions import NotFound
from eve.methods.delete import deleteitem_internal
from eve.methods.patch import patch_internal


def cascade_delete(resource, item):
    """Cascade DELETE.

    Hook to delete all objects, which have the 'cascade_delete' option set
    in the data_relation and relate to the object, which was just deleted.
    """
    domain = current_app.config['DOMAIN']

    deleted_id = item[domain[resource]['id_field']]

    for res, res_domain in domain.items():
        relations = ((field, field_def['data_relation'])
                     for field, field_def in res_domain['schema'].items()
                     if 'data_relation' in field_def and
                     field_def['data_relation'].get('resource') == resource)
        for field, data_relation in relations:
            if data_relation.get('cascade_delete'):
                # Delete all objects in resource `res`, which have `field` set
                # to item['_id']
                try:
                    deleteitem_internal(res, concurrency_check=False,
                                        **{field: deleted_id})
                except NotFound:
                    pass
            else:
                try:
                    patch_internal(res, payload={field: None},
                                   concurrency_check=False,
                                   **{field: deleted_id})
                except NotFound:
                    pass


def cascade_delete_collection(resource, items):
    """Hook to propagate the deletion of objects."""
    for item in items:
        cascade_delete(resource, item)


def init_app(app):
    """Add hooks to app."""
    app.on_deleted_item += cascade_delete
    app.on_deleted += cascade_delete_collection
