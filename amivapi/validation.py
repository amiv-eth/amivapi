# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
    amivapi.validation
    ~~~~~~~~~~~~~~~~~~~~~~~
    This extends the currently used validator to accept 'media' type
    Also adds hooks to validate other input
"""

import jsonschema

from flask import g, current_app as app
from werkzeug.datastructures import FileStorage
from imghdr import what

from eve_sqlalchemy.validation import ValidatorSQL
from eve.utils import request_method

from amivapi.utils import get_owner, get_class_for_resource
from amivapi.group_permissions import create_group_permissions_jsonschema


class ValidatorAMIV(ValidatorSQL):
    """ A Validator subclass adding more validation for special fields
    """

    def _validate_type_media(self, field, value):
        """ Enables validation for `media` data type.

        :param field: field name.
        :param value: field value.
        .. versionadded:: 0.3
        """
        if not isinstance(value, FileStorage):
            self._error(field, "file was expected, got '%s' instead." % value)

    def _validate_filetype(self, filetype, field, value):
        """ Validates filetype. Can validate images and pdfs

        Pdf: Check if first 4 characters are '%PDF' because that marks
        a PDF
        Image: Use imghdr library function what()

        Cannot validate others formats.

        :param filetype: List of filetypes, e.g. ['pdf', 'png']
        :param field: field name.
        :param value: field value.
        """
        if not((('pdf' in filetype) and (value.read(4) == r'%PDF')) or
               (what(value) in filetype)):
            self._error(field, "filetype not supported, has to be one of: " +
                        " %s" % str(filetype))

    def _validate_not_patchable(self, enabled, field, value):
        """ Custom Validator to inhibit patching of the field

        e.g. eventsignups, userid: required for post, but can not be patched

        :param enabled: Boolean, should be true
        :param field: field name.
        :param value: field value.
        """
        if enabled and (request_method() == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_not_patchable_unless_admin(self, enabled, field, value):
        """ Custom Validator to inhibit patching of the field

        e.g. eventsignups, userid: required for post, but can not be patched

        :param enabled: Boolean, should be true
        :param field: field name.
        :param value: field value.
        """
        if enabled and (request_method() == 'PATCH') and not g.resource_admin:
            self._error(field, "this field can not be changed with PATCH "
                        "unless you have admin rights.")

    def _validate_unique_combination(self, unique_combination, field, value):
        """ Custom validation if some fields are only unique in combination

        e.g. user with id 1 can have several eventsignups for different events,
        but only 1 eventsignup for event with id 42

        unique_combination should be a list of other fields

        Note: Make sure that other fields actually exists (setting them to
        required etc)

        :param unique_combination: list of fields
        :param field: field name.
        :param value: field value.
        """
        lookup = {field: value}  # self
        for other_field in unique_combination:
            lookup[other_field] = self.document.get(other_field)

        # If we are patching the issue is more complicated, some fields might
        # have to be checked but are not part of the document because they will
        # not be patched. We have to load them from the database
        patch = (request_method() == 'PATCH')
        if patch:
            original = self._original_document
            for key in unique_combination:
                if key not in self.document.keys():
                    lookup[key] = original[key]

        # Now check database
        if app.data.find_one(self.resource, None, **lookup) is not None:
            self._error(field, "value already exists in the database in " +
                        "combination with values for: %s" %
                        unique_combination)

    def _validate_only_self_enrollment_for_group(self, enabled, field, value):
        """ Validates if the id can be used to enroll for a group,

        Users can only sign up themselves
        Moderators and admins can sign up everyone

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group_id = self.document.get('group_id', None)
            group = app.data.find_one("groups", None, id=group_id)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                moderator_id = group["moderator_id"]

                if not(g.resource_admin or (g.logged_in_user == value) or
                       (g.logged_in_user == moderator_id)):
                    self._error(field, "You can only enroll yourself. (%s: "
                                "%s is yours)." % (field, g.logged_in_user))

    def _validate_self_enrollment_must_be_allowed(self, enabled, field, value):
        """ Validation for a group_id field in useraddressmembers
        Validates if the group allows self enrollment.

        Except group moderator and admins, they can ignore this

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group = app.data.find_one("groups", None, id=value)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                moderator_id = group["moderator_id"]
                if not(g.resource_admin or (g.logged_in_user == moderator_id)
                        or group["allow_self_enrollment"]):
                    # This copies the validation error for the case this group
                    # doesnt exist (since its hidden to the user)
                    self._error(field,
                                "value '%s' must exist in resource 'groups', "
                                "field 'id'." % value)

    def _validate_only_groups_you_moderate(self, enabled, field, value):
        """ Validation for a group_id field in forwardaddresses
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
            group = app.data.find_one("groups", None, id=value)

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
        """
        Validates the jsonschema provided using the python jsonschema library

        :param jsonschema: The jsonschema to use
        :param field: field name.
        :param value: field value.
        """
        schema = create_group_permissions_jsonschema(
            app.config['DOMAIN'].keys())

        try:
            jsonschema.validate(value, schema)
        except jsonschema.exceptions.ValidationError as v_error:
            # Something was not according to schema
            self._error(field, v_error.message)
