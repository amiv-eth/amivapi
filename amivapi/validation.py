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

from flask import g, current_app as app

from eve_sqlalchemy.validation import ValidatorSQL
from eve.utils import request_method


class ValidatorAMIV(ValidatorSQL):
    """ A Validator subclass adding more validation for special fields
    """

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
