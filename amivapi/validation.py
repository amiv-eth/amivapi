"""Custom Validator Class.

Custom validation rules defined here are used in multiple resources.
Validation rules used for single resources only can be found in the respective
resource directory.

Note the following phrase at the end of every validaton function docstring:
`The rule's arguments are validated against this schema:`

Cerberus expects this string followed by a schema in the docstring to
validate the schema itself.
[Read more](http://docs.python-cerberus.org/en/stable/customize.html)
"""

from datetime import datetime, timedelta, timezone
from imghdr import what

from eve.io.mongo import Validator as Validator
from flask import current_app as app
from flask import abort, g, request
from cerberus import TypeDefinition, utils


class ValidatorAMIV(Validator):
    """Validator subclass adding more validation for special fields."""

    @property
    def ignore_none_values(self):
        """Treat None values like missing fields for the `required` and
        `unique` validators.
        """
        return True

    types_mapping = Validator.types_mapping.copy()
    types_mapping['timedelta'] = TypeDefinition('timedelta', (timedelta,), ())

    def _validate_data_relation(self, data_relation, field, value):
        """Extend the arguments for data_relation to include cascading delete.

        The rule's arguments are validated against this schema:
        {'type': 'dict',
            'schema': {
                'resource': {'type': 'string', 'required': True},
                'field': {'type': 'string', 'required': True},
                'embeddable': {'type': 'boolean', 'default': False},
                'version': {'type': 'boolean', 'default': False},
                'cascade_delete': {'type': 'boolean', 'default': False}
            }
        }
        """
        super()._validate_data_relation(data_relation, field, value)

    def _validate_api_resources(self, enabled, field, value):
        """Value must be in api domain.

        Args:
            enabled (bool): Boolean, should be true to use the rule
            field (string): field name
            value (string): field value

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled and value not in app.config['DOMAIN']:
            self._error(field, "'%s' is not a api resource." % value)

    def _validate_not_patchable(self, enabled, field, _):
        """Inhibit patching of the field.

        e.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled (bool): Boolean, should be true to use the rule
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled and (request.method == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_not_patchable_unless_admin(self, enabled, field, _):
        """Inhibit patching of the field for non-admins.

        e.g. eventsignups, userid: required for post, but can not be patched

        Args:
            enabled (bool): Boolean, should be true to use the rule
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled and (request.method == 'PATCH') and not g.resource_admin:
            self._error(field, "this field can not be changed with PATCH "
                        "unless you have admin rights.")

    def _validate_admin_only(self, enabled, field, _):
        """Prohibit anyone except admins from setting this field.

        Applies to POST and PATCH.

        Args:
            enabled (bool): Boolean, should be true to use the rule
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled and not g.resource_admin:
            self._error(field,
                        "This field can only be set with admin permissions.")

    def _validate_unique_combination(self, unique_combination, field, value):
        """Validate that a combination of fields is unique.

        e.g. user with id 1 can have several eventsignups for different events,
        but only 1 eventsignup for event with id 42

        unique_combination should be a list of other fields

        Note: Make sure that other fields actually exists (setting them to
        required etc)

        Args:
            unique_combination (list of strings): combination fields
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'list', 'schema': {'type': 'string'}}
        """
        lookup = {field: value}  # self
        for other_field in unique_combination:
            lookup[other_field] = self.document.get(other_field)

        # If we are patching the issue is more complicated, some fields might
        # have to be checked but are not part of the document because they will
        # not be patched. We have to load them from the database
        if request.method == 'PATCH':
            original = self.persisted_document
            for key in unique_combination:
                if key not in self.document.keys():
                    lookup[key] = original[key]

        # Now check database
        if app.data.find_one(self.resource, None, **lookup) is not None:
            self._error(field, "value already exists in the database in " +
                        "combination with values for: %s" %
                        unique_combination)

    def _validate_depends_any(self, any_of_fields, field, _):
        """Validate, that any of the dependent fields is available

        Args:
            any_of_fields (list of strings): A list of fields. One of those
                                             fields must be provided.
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'list', 'schema': {'type': 'string'}}
        """
        if request.method == 'POST':
            for possible_field in any_of_fields:
                if possible_field in self.document:
                    return
            self._error(field, "May only be provided, if any of %s is set"
                        % ", ".join(any_of_fields))

    def _validate_filetype(self, allowed_types, field, value):
        """Validate filetype. Can validate images and pdfs.

        pdf: Check if first 4 characters are '%PDF' because that marks
        a PDF
        Image: Use imghdr library function what()

        Cannot validate others formats.

        Important: what() returns 'jpeg', NOT 'jpg', so 'jpg' will never be
        recognized!

        Args:
            allowed_types (list of strings): filetypes, e.g. ['pdf', 'png']
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'list', 'schema': {'type': 'string'}}
        """
        is_pdf = value.read(4) == br'%PDF'
        value.seek(0)  # Go back to beginning for what()
        filetype = 'pdf' if is_pdf else what(value)

        if filetype not in allowed_types:
            self._error(field, "filetype '%s' not supported, has to be in: "
                        "%s" % (filetype, allowed_types))

    def _validate_session_younger_than(self, threshold_timedelta, field, _):
        """Validation of the used token for special fields

        Validates if the session is not older than threshold_time

        Except admins, they can ignore this

        Args:
            threshold_timedelta (timedelta): threshold to compare with
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'timedelta'}
        """
        if threshold_timedelta < timedelta(seconds=0):
            # Use abort to actually give a stacktrace and break tests.
            abort(500, "Invalid field definition: %s: %s, "
                  "session_younger_than must be positive."
                  % (self.resource, field))

        if not g.get('resource_admin'):
            time_created = g.current_session['_created']
            time_now = datetime.now(timezone.utc)

            if time_now - time_created > threshold_timedelta:
                self._error(field, "Your session is too old. Using this field "
                            "is not allowed if your session is older than %s."
                            % threshold_timedelta)


# Cerberus uses a different validator for schemas, which is unaware of
# custom types.
# This validation class is created on the fly and cannot be chosen [1]
# The function to create a new validator [2] uses a fixed base validator
# (which is put into globals for some reason) [3], which we can replace with
# our type-aware AmivValidator
# 1: https://github.com/pyeve/cerberus/blob/1.1/cerberus/schema.py#L23-L24
# 2: https://github.com/pyeve/cerberus/blob/1.1/cerberus/utils.py#L69-L95
# 3: https://github.com/pyeve/cerberus/blob/1.1/cerberus/utils.py#L24-L28
utils.get_Validator_class = lambda: ValidatorAMIV
