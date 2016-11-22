# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Event Validation."""

import json
import pytz
from datetime import datetime

from flask import g, current_app, request

from eve.validation import SchemaError
from eve.utils import str_to_date


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
            self._error(field, "Must be json, parsing failed with exception: %s"
                        % str(e))
        else:
            try:
                self.validate_schema(json_data)
            except SchemaError as e:
                self._error(field, "does not contain a valid schema: %s"
                            % str(e))

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
            self._error(field, "Must be json, parsing failed with exception: %s"
                        % str(e))

        id_field = current_app.config['ID_FIELD']
        # At this point we have valid JSON, check for event now.
        # If PATCH, then event_id will not be provided, we have to find it
        if request.method == 'PATCH':
            lookup = {id_field: self._original_document['event']}
        elif ('event' in self.document.keys()):
            lookup = {id_field: self.document['event']}
        else:
            self._error(field, "Cannot evaluate additional fields "
                        "without event")

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

        # if event id is not valid another validator will fail anyway

    def _validate_signup_requirements(self, signup_possible, field, value):
        """Validate if signup requirements are met.

        Used for an event_id field - checks if the value "spots" is
        not -1. In this case there is no signup.

        Furthermore checks if current time is in the signup window for the
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
            event_id = self.document.get('event', None)
            lookup = {current_app.config['ID_FIELD']: event_id}
            event = current_app.data.find_one("events", None, **lookup)

            if event:
                if event['spots'] is None:
                    self._error(field, "the event with id %s has no signup"
                                % value)
                else:
                    # The event has signup, check if it is open
                    now = datetime.now(pytz.utc)
                    if now < event['time_register_start']:
                        self._error(field, "the signup for event with %s is "
                                    "not open yet." % value)
                    elif now > event['time_register_end']:
                        self._error(field, "the signup for event with id %s "
                                    "closed." % value)

                # If additional fields is missing still call the validator,
                # except an emtpy string, then the valid
                if (event.get('additional_fields', False) and
                        ('additional_fields' not in self.document.keys())):
                    # Use validator to get accurate errors
                    self._validate_type_json_event_field('additional_fields',
                                                         None)

    def _validate_only_self_enrollment_for_event(self, enabled, field, value):
        """Validate if the user can be used to enroll for an event.

        1.  Anyone can signup with no user id
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource admins: they can sign up others as well

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            if g.resource_admin or value is None:
                return
            if g.current_user != str(value):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.logged_in_user))

    def _validate_email_signup_must_be_allowed(self, enabled, field, value):
        """Validation for a event field in eventsignups.

        Validates if the event allows self enrollment.

        Except event moderator and admins, they can ignore this

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            # Get event
            event_id = self.document.get('event', None)
            lookup = {current_app.config['ID_FIELD']: event_id}
            event = current_app.data.find_one("events", None, **lookup)

            # If the event doesnt exist we do not have to do anything,
            # The 'type' validator will generate an error anyway
            if event is not None and not event["allow_email_signup"]:
                self._error(field,
                            "event %s does not allow signup with email address"
                            % event_id)

    def _validate_later_than(self, later_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than

        :param later_than: The field it will be compared to
        :param field: field name.
        :param value: field value.
        """
        if later_than in self.document:
            first_time = self.document[later_than]
        else:
            first_time = self._original_document[later_than]

        if not isinstance(first_time, datetime):
            # We need to parse the time for some reason
            first_time = str_to_date(first_time)

        if value < first_time:
            self._error(field, "Must be at a point in time after %s" %
                        later_than)

    def _validate_only_if_not_null(self, only_if_not_null,
                                   field, value):
        """The field may only be set if another field is not None.

        Args:
            depends_not_null (string): The field, that may not be None
            field (string): name of the validated field
            value: Value of the validated field
        """
        if self.document.get(only_if_not_null) is None:
            self._error(field, "May only be specified if %s is not null"
                        % only_if_not_null)
