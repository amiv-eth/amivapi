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
from collections import Hashable
from PIL import Image
from bs4 import BeautifulSoup

from eve.io.mongo import Validator as Validator
from flask import current_app as app
from flask import abort, g, request
from cerberus import TypeDefinition, utils


class ValidatorAMIV(Validator):
    """Validator subclass adding more validation for special fields.

    In particular, add a set of dummy rules (title, description, example,
    writeonly) that have no meaning for Cerberus, but allow to describe
    the schema in an OpenAPI fashion.

    (The documentation sub-module can also use this to generate a nice
    online documentation)
    """

    def _error(self, *args, **kwargs):
        """Fix annoying Cerberus behaviour.

        - Although it never uses it, Cerberus attaches the validated value
          silently to every error.

        - Whenever Cerberus collects errors, it deepcopies all of them for some
          reason.

        Now, if the validated value cannot be deepcopied, e.g. incoming file
        buffers, this causes Cerberus to crash, even though the value is
        *never* used during error processing.

        Thus, we remove the value from the error and the world is fine again.
        Luckily, Cerberus keeps a reference to the most recent created error,
        so we at least have a way to do that.

        See here:
        https://github.com/pyeve/cerberus/blob/master/cerberus/validator.py#L232
        """
        super()._error(*args, **kwargs)
        if hasattr(self, 'recent_error') and self.recent_error is not None:
            self.recent_error.value = None

    def _validate_title(*_):
        """{'type': 'string'}"""

    def _validate_description(*_):
        """{'type': 'string'}"""

    def _validate_example(*_):
        """{'type': [
            'number', 'boolean', 'string', 'list', 'dict', 'datetime'
        ]}"""

    def _validate_writeonly(*_):
        """{'type': 'boolean'}"""

    @property
    def ignore_none_values(self):
        """Treat None values like missing fields for the `required` and
        `unique` validators.
        """
        return True

    def _validate_excludes(self, excluded_fields, field, value):
        """Ignore 'None' for excluded fields.

        Hopefully Cerberus allows this at some point in the future, then
        we can remove this.

        The rule's arguments are validated against this schema:
        {'type': ('hashable', 'list'),
         'schema': {'type': 'hashable'}}
         """
        if isinstance(excluded_fields, Hashable):
            excluded_fields = [excluded_fields]

        # Remove None fields and unrequire them
        not_none = []
        for excluded in excluded_fields:
            if self.document.get(excluded) is None:
                self._unrequired_by_excludes.add(excluded)
            else:
                not_none.append(excluded)

        return super()._validate_excludes(not_none, field, value)

    types_mapping = Validator.types_mapping.copy()
    types_mapping['timedelta'] = TypeDefinition('timedelta', (timedelta,), ())
    types_mapping['tuple'] = TypeDefinition('tuple', (tuple,), ())

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

    def _validate_admin_only(self, enabled, field, value):
        """Prohibit anyone except admins from setting this field.

        Applies to POST and PATCH.

        Args:
            enabled (bool): Boolean, should be true to use the rule
            field (string): field name

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        # Due to how cerberus works, this rule is evaluated *after* default
        # values are set. We have to ensure that defaults are not rejected
        # on POST
        default_value = (request.method == 'POST' and
                         'default' in self.schema[field] and
                         self.schema[field]['default'] == value)

        if enabled and not g.resource_admin and not default_value:
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

    def _validate_aspect_ratio(self, aspect_ratio, field, value):
        """Validates aspect ratio of a given image.

        Args:
            aspect_ratio: a tuple of two numbers
                specifying the width relative to the height
            field (str): field name
            value (file): field value

        The rule's arguments are validated against this schema:
        {
            'type': 'tuple',
            'items': [{'type': 'number'}, {'type': 'number'}],
        }
        """
        width, height = aspect_ratio
        error = False
        # Load file (and reset stream so it can be saved correctly afterwards)
        img = Image.open(value)
        value.seek(0)

        if isinstance(height, int) and isinstance(width, int):
            # Strict ratio checking for ints
            # x/y == a/b is equal to xb == ay, which does not need division
            error = (img.size[0] * height) != (img.size[1] * width)
        else:
            # Non-integer ratios (e.g. DIN standard) need some tolerance
            diff = (img.size[0] / img.size[1]) - (width / height)
            error = abs(diff) > app.config['ASPECT_RATIO_TOLERANCE']

        if error:
            self._error(field, "The image does not have the required aspect "
                               "ratio. The accepted ratio is "
                               "%s:%s" % aspect_ratio)


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

    def _validate_no_html(self, no_html, field, value):
        """Validation for a text field.

        Validates that the provided text contains no HTML.

        Args:
            no_html (bool): if set to true, all text containing HTML will be
                            rejected
            field (string): field name
            value: field value

        Solution from [stack overflow](https://stackoverflow.com/a/24856208).

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if no_html and bool(BeautifulSoup(value, 'html.parser').find()):
            self._error(field, "The text must not contain html elements.")


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
