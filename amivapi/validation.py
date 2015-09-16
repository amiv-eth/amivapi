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

import json

from flask import request, current_app as app
from flask import g
from werkzeug.datastructures import FileStorage
from imghdr import what

from eve_sqlalchemy.validation import ValidatorSQL
from eve.methods.common import get_document
from eve.validation import SchemaError
from eve.utils import request_method

from amivapi import models, utils

from datetime import datetime


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

    def _validate_type_json_schema(self, field, value):
        """ Validates a cerberus schema saved as JSON

        1.  Is it JSON?
        2.  Is it a valid cerberus schema?

        :param field: field name.
        :param value: field value.
        """
        try:
            json_data = json.loads(value)
        except Exception as e:
            self._error(field, "Must be json, parsing failed with exception:" +
                        " %s" % str(e))
        else:
            try:
                self.validate_schema(json_data)
            except SchemaError as e:
                self._error(field, "additional_fields does not contain a " +
                            "valid schema: %s" % str(e))

    def _validate_type_json_event_field(self, field, value):
        """ Validates data in json format with event data

        1.  Is it JSON?
        2.  Try to find event
        3.  Validate schema and get all errors with prefix 'additional_fields:'

        :param field: field name.
        :param value: field value.
        """
        try:
            if value:
                data = json.loads(value)
            else:
                data = {}  # Do not crash if ''
        except Exception as e:
            self._error(field, "Must be json, parsing failed with exception:" +
                        " %s" % str(e))
        else:
            # At this point we have valid JSON, check for event now.
            # If PATCH, then event_id will not be provided, we have to find it
            if request_method() == 'PATCH':
                lookup = request.view_args
            else:
                if not('event_id' in self.document.keys()):
                    self._error(field, "Cannot evaluate additional field " +
                                "without event_id")
                lookup = {'_id': self.document['event_id']}

            # Use Eve method get_document to avoid accessing the db manually
            event = get_document('events', False, **lookup)

            # Load schema, we can use this without caution because only valid
            # json schemas can be written to the database
            if event:
                schema = json.loads(event['additional_fields'])
                v = app.validator(schema)  # Create a new validator
                v.validate(data)

                # Move errors to main validator
                for key in v.errors.keys():
                    self._error("%s: %s" % (field, key), v.errors[key])

    def _validate_if_this_then(self, if_this_then, field, value):
        """ Validates integer condition: Field exists and is > 0, then other
        fields must exist

        :param if_this_then: List of fields that are required if field > 0
        :param field: field name.
        :param value: field value.
        """
        if value > 0:
            for item in if_this_then:
                if item not in self.document.keys():
                    self._error(item, "Required field.")

    def _validate_later_than(self, later_than, field, value):
        """ Validates that field is at the same time or later than a given
        field

        :param later_than: The field it will be compared to
        :param field: field name.
        :param value: field value.
        """
        if value < self.document[later_than]:
            self._error(field, "Must be at a point in time after %s" %
                        later_than)

    def _validate_future_date(self, future_date, field, value):
        """ Enables validator for dates that need do be in the future

        If value is just now then there will be no error

        :param future_data: Boolean: Does it need to be in the future or not?
        :param field: field name.
        :param value: field value.
        """
        if future_date:
            if value < datetime.now():
                self._error(field, "date must be in the future.")
        else:
            if value > datetime.now():
                self._error(field, "date must not be in the future.")

    def _validate_not_patchable(self, not_patchable, field, value):
        """ Custom Validator to inhibit patching of the field

        e.g. eventsignups, userid: required for post, but can not be patched

        :param not_patchable: Boolean, should be true
        :param field: field name.
        :param value: field value.
        """
        if not_patchable and (request_method() == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_unique_combination(self, unique_combination, field, value):
        """ Custom validation if some fields are only unique in combination

        e.g. user with id 1 can have several eventsignups for different events,
        but only 1 eventsignup for event with id 42

        unique_combination should be a list: The first item in the list is the
        resource. This is not pretty but necessary to make the validator work
        for different resources

        Note: Make sure that other fields actually exists (setting them to
        required etc)

        :param unique_combination: list of fields, first entry must be target
                                   resource
        :param field: field name.
        :param value: field value.
        """
        # Step one: Remove resource from list
        resource = unique_combination[0]
        lookup = {field: value}  # First field
        for key in unique_combination[1:]:
            lookup[key] = self.document.get(key)  # all fields in combination

        # If we are patching the issue is more complicated, some fields might
        # have to be checked but are not part of the document because they will
        # not be patched. We have to load them from the database

        patch = (request_method() == 'PATCH')
        if patch:
            original = get_document(resource, False, **request.view_args)
            for key in unique_combination[1:]:
                if key not in self.document.keys():
                    lookup[key] = original[key]

        # Now check database
        # if the method is not post and the document is not the original,
        # there exists another instance
        data = get_document(resource, False, **lookup)
        if data and ((request_method() == 'POST') or
                     not (data['id'] == int(request.view_args['_id']))):
            self._error(field, "the field already exist in the database in " +
                        "combination with values for: %s" %
                        unique_combination[1:])

    def _validate_signup_requirements(self, signup_possible, field, value):
        """ Validate if signup requirements are met

        Used for an event_id field - checks if the value "spots" is
        not -1. In this case there is no signup.

        Furthermore checks if current time is in the singup window for the
        event.

        At last check if the event requires additional fields and display error
        if they are not present

        This will validate the additional fields with nothing as input to get
        errors as if additional_fields would be in the schema

        :param singup_possible: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if signup_possible:
            lookup = {'_id': value}
            event = get_document('events', False, **lookup)

            if event:
                if (event['spots'] == -1):
                    self._error(field, "the event with id %s has no signup" %
                                value)
                else:
                    # The event has signup, check if it is open
                    now = datetime.now()
                    if now < event['time_register_start']:
                        self._error(field, "the signup for event with %s is" +
                                    "not open yet." % value)
                    elif now > event['time_register_end']:
                        self._error(field, "the signup for event with id %s" +
                                    "closed." % value)

                # If additional fields is missing still call the validator,
                # except an emtpy string, then the valid
                if (event['additional_fields'] and
                        ('additional_fields' not in self.document.keys())):
                    # Use validator to get accurate errors
                    self._validate_type_json_event_field('additional_fields',
                                                         None)

    def _validate_only_anonymous(self, only_anonymous, field, valie):
        """ Makes sure that the user is anonymous.

        If you use this validator, ensure that there is a field 'user_id' in
        the same resource, e.g. by setting a dependancy

        :param only_anonymous: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if only_anonymous:
            if not(self.document['user_id'] == -1):
                self._error(field, "This field can only be set for anonymous "
                            "users with user_id -1")

    def _validate_public_check(self, public_check, field, value):
        """ Validates if event is public if value is -1

        This is a validation rule for a user_id field.

        If the signup is anonymous, the user has to be -1 and the event needs
        to be public

        The latter will be checked.

        :param public check: name of field with id of event. In current state
                             only works if set to 'event_id', but this
                             function could be extended in the future
        :param field: field name.
        :param value: field value.

        """
        # Implemented like this so it could be extended for other resources in
        # the future
        key = public_check
        resource = 'events'

        # Anonymous user
        if value == -1:
            lookup = {'id': self.document[key]}
            item = get_document(resource, False, **lookup)
            if not(item):
                self._error(field, "Can only be -1 if public. %s: %s does not "
                            "point to an existing resource" % (key, self
                                                               .document[key]))
            elif not(item['is_public']):
                self._error(field, "Can only be -1 if public. %s: %s does not "
                            "point to a public resource" % (key, self
                                                            .document[key]))

    def _validate_self_enroll(self, self_enroll, field, value):
        """ Validates if the id can be used to enroll for an event

        1.  -1 is a public id, anybody can use this (to e.g. sign up a friend
            via mail) (if public has to be determined somewhere else)
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource_admins: they can sign up others as well

        :param self_enroll: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if self_enroll:
            if not(g.resource_admin or (g.logged_in_user == value)):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.logged_in_user))

    def _validate_self_enroll_group(self, self_enroll, field, value):
        """ Validates if the id can be used to enroll for a group,
        a little more complex then for events

        1.  -1 is a public id, anybody can use this (to e.g. sign up a friend
            via mail) (if public has to be determined somewhere else)
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource_admins: they can sign up others as well
        4.  Groups: The group owner can add anyone as well

        :param self_enroll: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if self_enroll:
            owners = utils.get_owner(models.Group,
                                     self.document['group_id'])
            if not(g.resource_admin or (g.logged_in_user == value) or
                   (g.logged_in_user in owners)):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.logged_in_user))
