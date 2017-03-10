# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Event Validation."""

import json
import pytz
from datetime import datetime

from flask import g, current_app, request

from jsonschema import SchemaError, Draft4Validator


class EventValidator(object):
    """Custom Validator for event validation rules."""

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
        elif 'event' in self.document:
            lookup = {id_field: self.document['event']}
        else:
            # No event provided, the required validator of the event field
            # will complain.
            return

        event = current_app.data.find_one('events', None, **lookup)

        # Load schema, we can use this without caution because only valid
        # json schemas can be written to the database
        if event is not None:
            schema = json.loads(event['additional_fields'])
            v = Draft4Validator(schema)  # Create a new validator

            # search for errors and move them into main validator
            for error in v.iter_errors(data):
                self._error(field, error.message)

        # if event id is not valid another validator will fail anyway

    def _validate_signup_requirements(self, signup_possible, field, event_id):
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
            # We can assume event_id is valid, as the type validator will abort
            # otherwise and this validator is not executed
            lookup = {current_app.config['ID_FIELD']: event_id}
            event = current_app.data.find_one("events", None, **lookup)

            if event['spots'] is None:
                self._error(field, "the event with id %s has no signup"
                            % event_id)
                return

            # The event has signup, check if it is open
            if not g.get('resource_admin'):
                now = datetime.now(pytz.utc)
                if now < event['time_register_start']:
                    self._error(field, "the signup for event with %s is "
                                "not open yet." % event_id)
                elif now > event['time_register_end']:
                    self._error(field, "the signup for event with id %s "
                                "closed." % event_id)

            # If additional fields is missing still call the validator,
            # so correct error messages are produced
            if (event.get('additional_fields') and
                    ('additional_fields' not in self.document.keys())):
                self._validate_type_json_event_field('additional_fields',
                                                     None)

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

    """
    General purpose validators
    """

    def _validate_type_json_schema_object(self, field, value):
        """Validate a cerberus schema saved as JSON.

        1.  Is it JSON?
        2.  Does it satisfy our restrictions for jsonschemas?
        3.  Is it a valid json-schema?

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
            # validate if these fields are included exactly as given
            # (we, e.g., always require objects so UI can rely on this)
            enforced_fields = {
                '$schema': 'http://json-schema.org/draft-04/schema#',
                'type': 'object',
                'additionalProperties': False
            }

            for key, value in enforced_fields.items():
                if key not in json_data or json_data[key] != value:
                    self._error(field,
                                "'{key}' is required to be set to '{value}'"
                                .format(key=key, value=value))

            try:
                # now check if it is entirely valid jsonschema
                v = Draft4Validator(json_data)
                # by default, jsonschema specification allows unknown properties
                # We do not allow these.
                v.META_SCHEMA['additionalProperties'] = False
                v.check_schema(json_data)
            except SchemaError as e:
                self._error(field, "does not contain a valid schema: %s"
                            % str(e))

    # Eve doesn't handle time zones properly. Its always UTC but sometimes
    # the timezone is included, sometimes it isn't.

    def _get_time(self, fieldname):
        """Retrieve time field from document or _original_document."""
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
        doc = self.document
        exists_in_original = (  # Check original document in case of patches
            self._original_document is not None and
            self._original_document.get(only_if_not_null) is not None)

        if doc.get(only_if_not_null) is None and not exists_in_original:
            self._error(field, "May only be specified if %s is not null"
                        % only_if_not_null)

    def _validate_required_if_not(self, *args):
        """Dummy function for Cerberus.(It complains if it can find the rule).

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
