from imghdr import what
from typing import Any, Iterable

from eve.io.mongo import Validator
from flask import current_app as app
from flask import g, request


class ValidatorAMIV(Validator):
    """Validator subclass adding more validation for special fields."""

    def _validate_api_resources(
            self, enabled: bool, field: str, value: str) -> None:
        """Value must be in api domain."""
        if enabled and value not in app.config['DOMAIN']:
            self._error(field, "'%s' is not a api resource." % value)

    def _validate_not_patchable(
            self, enabled: bool, field: str, value: Any) -> None:
        """Custom Validator to inhibit patching of the field.

        E.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled: Boolean, should be true
            field: field name.
            value: field value.
        """
        if enabled and (request.method == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_not_patchable_unless_admin(
            self, enabled: bool, field: str, value: Any) -> None:
        """Inhibit patching of the field.

        E.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled: Boolean, should be true
            field: field name.
            value: field value.
        """
        if enabled and (request.method == 'PATCH') and not g.resource_admin:
            self._error(field, "this field can not be changed with PATCH "
                        "unless you have admin rights.")

    def _validate_admin_only(
            self, enabled: bool, field: str, value: Any) -> None:
        """Prohibit anyone except admins from setting this field."""
        if enabled and not g.resource_admin:
            self._error(field, "This field can only be set with admin "
                        "permissions.")

    def _validate_unique_combination(self,
                                     unique_combination: Iterable[str],
                                     field: str, value: Any) -> None:
        """Validate that a combination of fields is unique.

        e.g. user with id 1 can have several eventsignups for different events,
        but only 1 eventsignup for event with id 42

        unique_combination should be a list of other fields

        Note: Make sure that other fields actually exists (setting them to
        required etc)

        Args:
            unique_combination: combination fields
            field: field name.
            value: field value.
        """
        lookup = {field: value}  # self
        for other_field in unique_combination:
            lookup[other_field] = self.document.get(other_field)

        # If we are patching the issue is more complicated, some fields might
        # have to be checked but are not part of the document because they will
        # not be patched. We have to load them from the database
        if request.method == 'PATCH':
            original = self._original_document
            for key in unique_combination:
                if key not in self.document.keys():
                    lookup[key] = original[key]

        # Now check database
        if app.data.find_one(self.resource, None, **lookup) is not None:
            self._error(field, "value already exists in the database in " +
                        "combination with values for: %s" %
                        unique_combination)

    def _validate_depends_any(self, any_of_fields: Iterable[str], field: str,
                              value: Any) -> None:
        """Validate, that any of the dependent fields is available

        Args:
            any_of_fields (list of strings): A list of fields. One of those
                                             fields must be provided.
            field (string): This fields name
            value: This fields value
        """
        if request.method == 'POST':
            for possible_field in any_of_fields:
                if possible_field in self.document:
                    return
            self._error(field, "May only be provided, if any of %s is set"
                        % ", ".join(any_of_fields))

    def _validate_filetype(self, filetype: Iterable[str], field: str,
                           value: Any) -> None:
        """Validate filetype. Can validate images and pdfs.

        pdf: Check if first 4 characters are '%PDF' because that marks
        a PDF
        Image: Use imghdr library function what()

        Cannot validate others formats.

        Important: what() returns 'jpeg', NOT 'jpg', so 'jpg' will never be
        recognized!

        Args:
            filetype: filetypes, e.g. ['pdf', 'png']
            field: field name.
            value: field value.
        """
        is_pdf = value.read(4) == br'%PDF'
        value.seek(0)  # Go back to beginning for what()
        t = 'pdf' if is_pdf else what(value)

        if not(t in filetype):
            self._error(field, "filetype '%s' not supported, has to be in: "
                        "%s" % (t, filetype))
