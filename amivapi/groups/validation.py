# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event Validation.

Also has method to create group_permissions_jsonschema.
"""

from flask import current_app, g


class GroupValidator(object):
    """Custom Validator for group validation rules."""

    def _validate_only_self_or_moderator(self, enabled, field, value):
        """Validate if the id can be used to enroll for a group.

        Users can only sign up themselves
        Moderators and admins can sign up everyone
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

    def _validate_api_resources(self, enabled, field, value):
        """Value must be in api domain."""
        if enabled and value not in current_app.config['DOMAIN']:
            self._error(field, "'%s' is not a api resource." % value)
