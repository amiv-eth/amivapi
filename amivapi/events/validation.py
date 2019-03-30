# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Event Validation."""
from datetime import datetime
import json

from flask import current_app, g, request
from jsonschema import Draft4Validator, SchemaError
import pytz


class EventValidator(object):
    """Custom Validator for event validation rules."""

    def _validate_json_event_field(self, enabled, field, value):
        """Validate data in json format with event data.

        1.  Is it JSON?
        2.  Try to find event
        3.  Validate schema and get all errors with prefix 'additional_fields:'

        Args:
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if not enabled:
            return

        try:
            data = json.loads(value) if value else {}  # Do not crash if ''
        except json.JSONDecodeError as e:
            self._error(field,
                        "Must be json, parsing failed with exception: %s" % e)
            return

        id_field = current_app.config['ID_FIELD']
        # At this point we have valid JSON, check for event now.
        # If PATCH, then event_id will not be provided, we have to find it
        if request.method == 'PATCH':
            lookup = {id_field: self.persisted_document['event']}
        elif 'event' in self.document:
            lookup = {id_field: self.document['event']}
        else:
            # No event provided, the `required` validator of the event field
            # will complain, but we can't continue here
            return

        event = current_app.data.find_one('events', None, **lookup)

        # Load schema, we can use this without caution because only valid
        # json schemas can be written to the database
        if event is not None:
            schema = json.loads(event['additional_fields'])
            validator = Draft4Validator(schema)

            # search for errors and move them into main validator
            for error in validator.iter_errors(data):
                self._error(field, error.message)

    def _validate_not_blacklisted(self, enabled, field, user_id):
        """Validate if the user is not on the blacklist.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if enabled:
            count = current_app.data.driver.db['blacklist'].count_documents({
                        'user': user_id,
                        '$or': [{'end_time': None},
                                {'end_time': {'$gte': datetime.utcnow()}}]})
            if count:
                self._error(field, "the user with id %s is on the blacklist"
                            % user_id)

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
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
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
                self._validate_json_event_field(True,
                                                'additional_fields',
                                                '')

    def _validate_email_signup_must_be_allowed(self, enabled, field, _):
        """Validation for an event field in eventsignups.

        Validates if the event allows self enrollment.

        Except event moderator and admins, they can ignore this

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
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

    def _validate_json_schema(self, enabled, field, value):
        """Validate a json schema[1] string.

        1.  Is the string valid JSON?
        2.  Does it satisfy our restrictions for jsonschemas?
        3.  Is it a valid json-schema?

        Args:
            field (string): field name
            value: field value

        1: https://json-schema.org

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        if not enabled:
            return

        try:
            json_data = json.loads(value)
        except json.JSONDecodeError as error:
            self._error(field,
                        "Invalid json, parsing failed with exception: %s"
                        % error)
            return

        # validate if these fields are included exactly as given
        # (we, e.g., always require objects so UI can rely on this)
        enforced_fields = {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'object',
            'additionalProperties': False
        }

        for key, val in enforced_fields.items():
            if key not in json_data or json_data[key] != val:
                self._error(field,
                            "'%s' is required to be set to '%s'"
                            % (key, val))

        # now check if it is entirely valid jsonschema
        validator = Draft4Validator(json_data)
        # by default, jsonschema specification allows unknown properties
        # We do not allow these.
        validator.META_SCHEMA['additionalProperties'] = False

        try:
            validator.check_schema(json_data)
        except SchemaError as error:
            self._error(field, "does not contain a valid schema: %s"
                        % error)

    # Eve doesn't handle time zones properly. It's always UTC but sometimes
    # the timezone is included, sometimes it isn't.

    def _get_time(self, fieldname):
        """Retrieve time field from document or original document."""
        # Try to pick the value from document first, fall back to original
        time = self.document.get(fieldname)
        if time is None:
            time = (self.persisted_document[fieldname]
                    if self.persisted_document else None)

        if time is None:
            return time

        if isinstance(time, datetime):
            return time.replace(tzinfo=None)
        else:
            try:
                date_format = current_app.config['DATE_FORMAT']
                return datetime.strptime(time, date_format).replace(tzinfo=None)
            except ValueError:
                return None

    def _validate_later_than(self, later_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than

        Args:
            later_than (str): Name of other field for comparison
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'string'}
        """
        other_time = self._get_time(later_than)
        if other_time is None:
            return  # Other time has wrong format, will be caught by validator

        if value.replace(tzinfo=None) <= other_time:
            self._error(field, "Must be at a point in time after %s" %
                        later_than)

    def _validate_earlier_than(self, earlier_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than

        Args:
            earlier_than (str): Name of other field for comparison
            field (string): field name
            value: field value

        The rule's arguments are validated against this schema:
        {'type': 'string'}
        """
        other_time = self._get_time(earlier_than)
        if other_time is None:
            return

        if value.replace(tzinfo=None) >= other_time:
            self._error(field, "Must be at a point in time before %s" %
                        earlier_than)

    def _validate_only_if_not_null(self, only_if_not_null, field, _):
        """The field may only be set if another field is not None.

        Args:
            only_if_not_null (string): The field, that may not be None
            field (string): name of the validated field

        The rule's arguments are validated against this schema:
        {'type': 'string'}
        """
        doc = self.document
        exists_in_original = (  # Check original document in case of patches
            self.persisted_document is not None and
            self.persisted_document.get(only_if_not_null) is not None)

        if doc.get(only_if_not_null) is None and not exists_in_original:
            self._error(field, "May only be specified if %s is not null"
                        % only_if_not_null)

    def _validate_no_user_mail(self, enabled, field, value):
        """Validate that the mail address does not belong to a user.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        users = current_app.data.driver.db['users']
        if enabled and users.find({'email': value}).count() > 0:
            self._error(field, "The email address '%s' "
                               "is already registered with a user and cannot "
                               "be used for public signup." % value)

    def _validate_required_if_not(self, *args):
        """Dummy function for Cerberus.(It complains if it can find the rule).

        Functionality is implemented in the required field validation.

        The rule's arguments are validated against this schema:
        {'type': 'string'}
        """

    def _BareValidator__validate_required_fields(self, document):
        """Extend the validation of requirements to support `required_if_not`.

        Needed for language fields, where either german or english is needed.
        The new requirement validator will (in addition to the default
        `required` field) check for a a `required_`

        Note on the weird name:
        Cerberus defines the validation of required fields with double
        underscores. Such variables undergo 'name mangling' in python,
        and `__func` is replaced by `_classname_func` in the class definition,
        a mechanism to avoid name collisions [1].

        However, we precisely need to overwrite this function, hence
        the weird name, as it is defined in the Cerberus `BareValidator` class.


        1: https://docs.python.org/3/tutorial/classes.html#tut-private
        """
        super()._BareValidator__validate_required_fields(document)

        for field, schema in self.schema.items():
            # If the field is there do nothing
            if field not in document:
                req_dep = schema.get('required_if_not')
                if req_dep is not None and req_dep not in document:
                    self._error(field,
                                "'%s' is required if '%s' is not present."
                                % (field, req_dep))
