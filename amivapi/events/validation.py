# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event Validation."""

import json
from datetime import datetime

from flask import g, current_app

from eve.utils import request_method
from eve.validation import SchemaError


class EventValidator(object):
    """Custom Validator for event validation rules."""

    def _validate_type_json_schema(self, field, value):
        """Validate a cerberus schema saved as JSON.

        1.  Is it JSON?
        2.  Is it a valid cerberus schema?

        Args:
            field (string): field name.
            value: field value.
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
        """Validate data in json format with event data.

        1.  Is it JSON?
        2.  Try to find event
        3.  Validate schema and get all errors with prefix 'additional_fields:'

        Args:
            field (string): field name.
            value: field value.
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

            event = current_app.data.find_one('events', None, **lookup)

            # Load schema, we can use this without caution because only valid
            # json schemas can be written to the database
            if event is not None:
                schema = json.loads(event['additional_fields'])
                v = current_app.validator(schema)  # Create a new validator
                v.validate(data)

                # Move errors to main validator
                for key in v.errors.keys():
                    self._error("%s: %s" % (field, key), v.errors[key])

    def _validate_signup_requirements(self, signup_possible, field, value):
        """Validate if signup requirements are met.

        Used for an event_id field - checks if the value "spots" is
        not -1. In this case there is no signup.

        Furthermore checks if current time is in the singup window for the
        event.

        At last check if the event requires additional fields and display error
        if they are not present

        This will validate the additional fields with nothing as input to get
        errors as if additional_fields would be in the schema

        Args:
            singup_possible (bool); validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if signup_possible:
            event = current_app.data.find_one('events', None, id=value)

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

    def _validate_only_self_enrollment_for_event(self, enabled, field, value):
        """Validate if the id can be used to enroll for an event.

        1.  -1 is a public id, anybody can use this (to e.g. sign up a friend
            via mail) (if public has to be determined somewhere else)
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource_admins: they can sign up others as well

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            if not(g.resource_admin or (g.logged_in_user == value)):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.logged_in_user))

    def _validate_email_signup_must_be_allowed(self, enabled, field, value):
        """Validation for a event_id field in eventsignups.

        Validates if the event allows self enrollment.

        Except event moderator and admins, they can ignore this

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            # Get event
            event_id = self.document.get('event_id', None)
            event = current_app.data.find_one("events", None, id=event_id)

            # If the event doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if event is not None and not(event["allow_email_signup"]):
                self._error(field,
                            "event with id '%s' does not allow signup with "
                            "email address." % event_id)

    def _validate_only_anonymous(self, only_anonymous, field, valie):
        """Make sure that the user is anonymous.

        If you use this validator, ensure that there is a field 'user_id' in
        the same resource, e.g. by setting a dependancy

        Args:
            only_anonymous (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if only_anonymous:
            if not(self.document.get('user_id', None) == -1):
                self._error(field, "This field can only be set for anonymous "
                            "users with user_id -1")

    def _validate_later_than(self, later_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than

        :param later_than: The field it will be compared to
        :param field: field name.
        :param value: field value.
        """
        if value < self.document[later_than]:
            self._error(field, "Must be at a point in time after %s" %
                        later_than)

    def _validate_if_this_then(self, if_this_then, field, value):
        """Validate integer condition.

        if value > 0, then other fields must exist

        Args:
            if_this_then (list): fields that are required if value > 0.
            field (string): field name.
            value: field value.
        """
        if value > 0:
            for item in if_this_then:
                if item not in self.document.keys():
                    self._error(item, "Required field.")
