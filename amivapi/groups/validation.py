# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Group Validation.

Also has method to create group_permissions_jsonschema.
"""

from flask import current_app, g


class GroupValidator(object):
    """Custom Validator for group validation rules."""

    def _validate_only_self_or_moderator(self, enabled, field, value):
        """Validate if the id can be used to enroll for a group.

        Users can only sign up themselves
        Moderators and admins can sign up everyone

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled and not g.get('resource_admin'):
            # Get moderator id
            group_id = self.document['group']
            group = current_app.data.find_one('groups', None, _id=group_id)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group:
                user_id = g.get('current_user')
                if user_id not in (str(value), str(group.get('moderator'))):
                    self._error(
                        field, "You can only enroll yourself. (Your id: "
                        "%s)" % (user_id))

    def _validate_self_enrollment_required(self, enabled, field, value):
        """Check self_enrollment for group.

        Validates if the group allows self enrollment.
        Group moderator and admins can enroll anyway.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled and not g.get('resource_admin'):
            # Check if moderator
            group = current_app.data.find_one('groups', None, _id=value)
            moderator = group.get('moderator')
            if not (group.get('allow_self_enrollment') or
                    (moderator and str(moderator) == g.get('current_user'))):
                self._error(field,
                            "Group with id '%s' does not allow self enrollment"
                            " and you are not the group moderator.")

    def _validate_unique_elements(self, enabled, field, value):
        """Validate that a list does only contain unique elements.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled:
            if len(value) > len(set(value)):
                self._error(field, "All list elements must be unique.")

    def _validate_unique_elements_for_resource(self, enabled, field, value):
        """Validate that no list elements exists in another items list.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled:
            # Ignore values already present in original document if updating
            if self.persisted_document is not None:
                old_list = self.persisted_document.get(field, [])
                elements = (e for e in value if e not in old_list)
            else:
                elements = value

            errors = []
            for element in elements:
                group = current_app.data.driver.db['groups'].find_one(
                    {field: element}, {'_id': 1})
                if group:
                    errors.append(element)
            if errors:
                self._error(field, "The following values already exist in "
                            "other items: " + ", ".join(errors))
