"""
    amivapi.validation
    ~~~~~~~~~~~~~~~~~~~~~~~
    This extends the currently used validator to accept 'media' type
"""

from eve_sqlalchemy.validation import ValidatorSQL
from werkzeug.datastructures import FileStorage


class ValidatorAMIV(ValidatorSQL):
    """ A cerberus.Validator subclass adding the `unique` constraint to
    Cerberus standard validation. For documentation please refer to the
    Validator class of the eve.io.mongo package.
    """

    def _validate_type_media(self, field, value):
        """ Enables validation for `media` data type.
        :param field: field name.
        :param value: field value.
        .. versionadded:: 0.3
        """
        if not isinstance(value, FileStorage):
            self._error(field, "file was expected, got '%s' instead." % value)
