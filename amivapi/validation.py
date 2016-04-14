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
import jsonschema

from flask import g, current_app as app
from werkzeug.datastructures import FileStorage
from imghdr import what

from eve_sqlalchemy.validation import ValidatorSQL
from eve.validation import SchemaError
from eve.utils import request_method

from amivapi.utils import get_owner, get_class_for_resource
from amivapi.group_permissions import create_group_permissions_jsonschema

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
                lookup = {'id': self._original_document['event_id']}
            elif ('event_id' in self.document.keys()):
                lookup = {'id': self.document['event_id']}
            else:
                self._error(field, "Cannot evaluate additional fields " +
                                   "without event_id")
                return

            event = app.data.find_one('events', None, **lookup)

            # Load schema, we can use this without caution because only valid
            # json schemas can be written to the database
            if event is not None:
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
            event = app.data.find_one('events', None, id=value)

            if event:
                if (event['spots'] == -1):
                    self._error(field, "the event with id %s has no signup" %
                                value)
                else:
                    # The event has signup, check if it is open
                    now = datetime.utcnow()
                    if now < event['time_register_start']:
                        self._error(field, "the signup for event with %s is"
                                    "not open yet." % value)
                    elif now > event['time_register_end']:
                        self._error(field, "the signup for event with id %s"
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
            if not(self.document.get('user_id', None) == -1):
                self._error(field, "This field can only be set for anonymous "
                            "users with user_id -1")

    def _validate_only_self_enrollment_for_event(self, enabled, field, value):
        """ Validates if the id can be used to enroll for an event

        1.  -1 is a public id, anybody can use this (to e.g. sign up a friend
            via mail) (if public has to be determined somewhere else)
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource_admins: they can sign up others as well

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            if not(g.resource_admin or (g.logged_in_user == value)):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.logged_in_user))

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

    def _validate_email_signup_must_be_allowed(self, enabled, field, value):
        """ Validation for a event_id field in eventsignups
        Validates if the group allows self enrollment.

        Except group moderator and admins, they can ignore this

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get event
            event_id = self.document.get('event_id', None)
            event = app.data.find_one("events", None, id=event_id)

            # If the event doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if event is not None and not(event["allow_email_signup"]):
                self._error(field,
                            "event with id '%s' does not allow signup with "
                            "email address." % event_id)

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
