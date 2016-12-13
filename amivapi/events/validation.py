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

            if not event:
                return

            if event['spots'] is None:
                self._error(field, "the event with id %s has no signup"
                            % value)
                return

            # The event has signup, check if it is open
            if not g.get('resource_admin'):
                now = datetime.now(pytz.utc)
                if now < event['time_register_start']:
                    self._error(field, "the signup for event with %s is "
                                "not open yet." % value)
                elif now > event['time_register_end']:
                    self._error(field, "the signup for event with id %s "
                                "closed." % value)

            # If additional fields is missing still call the validator,
            # so correct error messages are produced
            if (event.get('additional_fields') and
                ('additional_fields' not in self.document.keys())):
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

    # Eve doesn't handle time zones properly. Its always UTC but sometimes
    # the timezone is included, sometimes it isn't.

    def _get_time(self, fieldname):
        """Retrieve time field from document or _original_document.
        """
        # Try to pick the value from document first, fall back to original
        time = self.document.get(fieldname)
        if time is None:
            time = (self._original_document[fieldname]
                    if self._original_document else None)

        if time is None:
            return None

        return time.replace(tzinfo=None)

    def _validate_later_than(self, later_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than
        """
        other_time = self._get_time(later_than)
        if other_time is None:
            return

        if value.replace(tzinfo=None) <= other_time:
            self._error(field, "Must be at a point in time after %s" %
                        later_than)

    def _validate_earlier_than(self, earlier_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than
        """
        other_time = self._get_time(earlier_than)
        if other_time is None:
            return

        if value.replace(tzinfo=None) >= other_time:
            self._error(field, "Must be at a point in time before %s" %
                        earlier_than)

    def _validate_only_if_not_null(self, only_if_not_null,
                                   field, value):
        """The field may only be set if another field is not None.

        Args:
            only_if_not_null (string): The field, that may not be None
            field (string): name of the validated field
            value: Value of the validated field
        """
        if self.document.get(only_if_not_null) is None:
            self._error(field, "May only be specified if %s is not null"
                        % only_if_not_null)

    def _validate_required_if_not(self, *args):
        """Dummy function for Cerberus (It complains if it can find the rule).

        Functionality is implemented in the requierd field validation.
        """

    def _validate_required_fields(self, document):
        """Extend the parsing of to support requirements depending on fields.

        Needed for language fields, where either german or english is needed.
        The new requirement validator will (in addition to the default
        `required` field) check for a a `required_`
        """
        super(EventValidator, self)._validate_required_fields(document)

        for field, schema in self.schema.items():
            # If the field is there do nothing
            if field not in document:
                req_dep = schema.get('required_if_not')
                if req_dep is not None and req_dep not in document:
                    self._error(field,
                                "'%s' is required if '%s' is not present."
                                % (field, req_dep))
