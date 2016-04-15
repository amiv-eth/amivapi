# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event Validation.

Also has method to create group_permissions_jsonschema.
"""

import jsonschema

from flask import g, current_app

from amivapi.utils import get_owner, get_class_for_resource


def create_group_permissions_jsonschema():
    """Create a jsonschema of valid group permissions.

    Returns:
        (dict) the jsonschema
    """
    # Create outer container
    # Properties will be the enpoints
    # additionalProperties has to be false, otherwise all unknown properties
    # are accepted
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Permission Matrix Schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {}
    }

    # Now add endpoints as allowed properties
    # This is the inner container, they are again objects
    for res in current_app.config['DOMAIN']:
        schema["properties"][res] = {
            "title": "Permissions for '%s' resource" % res,
            "type": "object",
            "additionalProperties": False,
            "properties": {}
        }

        subschema = schema["properties"][res]["properties"]

        # All basic methods covered, just boolean
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            subschema[method] = {
                "title": 'Permission for %s' % method,
                "type": "boolean"
            }

    return schema


class GroupValidator(object):
    """Custom Validator for group validation rules."""

    def _validate_only_self_enrollment_for_group(self, enabled, field, value):
        """Validate if the id can be used to enroll for a group.

        Users can only sign up themselves
        Moderators and admins can sign up everyone

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group_id = self.document.get('group_id', None)
            group = current_app.data.find_one("groups", None, id=group_id)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                moderator_id = group["moderator_id"]

                if not(g.resource_admin or (g.logged_in_user == value) or
                       (g.logged_in_user == moderator_id)):
                    self._error(field, "You can only enroll yourself. (%s: "
                                "%s is yours)." % (field, g.logged_in_user))

    def _validate_self_enrollment_must_be_allowed(self, enabled, field, value):
        """Validation for a group_id field in useraddressmembers.

        Validates if the group allows self enrollment.

        Except group moderator and admins, they can ignore this

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group = current_app.data.find_one("groups", None, id=value)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                moderator_id = group["moderator_id"]
                if not(g.resource_admin or
                       (g.logged_in_user == moderator_id) or
                       group["allow_self_enrollment"]):
                    # This copies the validation error for the case this group
                    # doesnt exist (since its hidden to the user)
                    self._error(field,
                                "value '%s' must exist in resource 'groups', "
                                "field 'id'." % value)

    def _validate_only_groups_you_moderate(self, enabled, field, value):
        """Validation for a group_id field in forwardaddresses.

        If you are not member or admin of the group you get the same
        error as if the group wouldn't exist

        If you are member, but not moderator, you will get a message that you
        cannot enter this group_id

        If you are moderator or have admin permissions it is alright.

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group = current_app.data.find_one("groups", None, id=value)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                if not g.resource_admin:
                    moderator_id = group["moderator_id"]
                    if not(g.logged_in_user == moderator_id):
                        owners = get_owner(get_class_for_resource("groups"),
                                           value)
                        if g.logged_in_user in owners:
                            self._error(field, "you are not the moderator of"
                                        "this group.")
                        else:
                            # Not Member either
                            # Copies the validation error for the case this
                            # group doesnt exist (since its hidden to the user)
                            self._error(field,
                                        "value '%s' must exist in resource "
                                        "'groups', field 'id'." % value)

    def _validate_type_permissions_jsonschema(self, field, value):
        """Validate jsonschema provided using the python jsonschema library.

        :param jsonschema: The jsonschema to use
        :param field: field name.
        :param value: field value.
        """
        schema = create_group_permissions_jsonschema()

        try:
            jsonschema.validate(value, schema)
        except jsonschema.exceptions.ValidationError as v_error:
            # Something was not according to schema
            self._error(field, v_error.message)
