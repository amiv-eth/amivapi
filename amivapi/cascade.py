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

from typing import Iterable

from eve import Eve
from eve.methods.delete import deleteitem_internal
from eve.methods.patch import patch_internal
from flask import current_app
from werkzeug.exceptions import NotFound

from amivapi.utils import admin_permissions


def cascade_delete(resource: str, item: dict) -> None:
    """Cascade DELETE.

    Hook to delete all objects, which have the 'cascade_delete' option set
    in the data_relation and relate to the object, which was just deleted.
    """
    domain = current_app.config['DOMAIN']
    deleted_id = item[domain[resource]['id_field']]

    for res, res_domain in domain.items():
        # Filter schema of `res` to get all fields containing references
        # to the resource of the deleted item
        relations = ((field, field_def['data_relation'])
                     for field, field_def in res_domain['schema'].items()
                     if 'data_relation' in field_def and
                     field_def['data_relation'].get('resource') == resource)
        for field, data_relation in relations:
            # All items in `res` with reference to the deleted item
            lookup = {field: deleted_id}
            with admin_permissions():
                try:
                    if data_relation.get('cascade_delete'):
                        # Delete the item as well
                        deleteitem_internal(res, concurrency_check=False,
                                            **lookup)
                    else:
                        # Don't delete, only remove reference
                        patch_internal(res, payload={field: None},
                                       concurrency_check=False,
                                       **lookup)
                except NotFound:
                    pass


def cascade_delete_collection(resource: str, items: Iterable[dict]) -> None:
    """Hook to propagate the deletion of objects."""
    for item in items:
        cascade_delete(resource, item)


def init_app(app: Eve) -> None:
    """Add hooks to app."""
    app.on_deleted_item += cascade_delete
    app.on_deleted += cascade_delete_collection
