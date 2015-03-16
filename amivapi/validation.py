# -*- coding: utf-8 -*-
#
# AMIVAPI validation.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    amivapi.validation
    ~~~~~~~~~~~~~~~~~~~~~~~
    This extends the currently used validator to accept 'media' type
    Also adds hooks to validate other input
"""

import datetime as dt
import json

from flask import request, current_app as app
from flask import abort, g
from werkzeug.datastructures import FileStorage
from imghdr import what

from eve_sqlalchemy.validation import ValidatorSQL
from eve.methods.common import get_document
from eve.validation import SchemaError
from eve.utils import debug_error_message, request_method

from amivapi import models

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
        filetyp should be a list like ['pdf', 'jpeg', 'png']
        Pdf: Check if first 4 characters are '%PDF' because that marks
        a PDF
        Image: Use imghdr library function what()
        Cannot validate others formats.
        """
        if not((('pdf' in filetype) and (value.read(4) == r'%PDF')) or
               (what(value) in filetype)):
            self._error(field, "filetype not supported, has to be one of: " +
                        " %s" % str(filetype))

    def _validate_type_json_schema(self, field, value):
        """ Enables validation for schema fields in json-Format.
        Will check both if it is json and if it is a correct schema"""
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
        """ Validates data in json format that has to correspond to the schema
        saved in the event
        Uses a internal validator and passes all errors to the main validator
        (After adding the prefix: "Additional_fields: ...")
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

    def _validate_future_date(self, future_date, field, value):
        """ Enables validator for dates that need do be in the future"""
        if future_date:
            if value <= datetime.now():
                self._error(field, "date must be in the future.")
        else:
            if value > datetime.now():
                self._error(field, "date must not be in the future.")

    def _validate_not_patchable(self, not_patchable, field, value):
        """ Custom Validator to inhibit patching of the field
        e.g. eventsignups, userid: can be posted but not patched
        """
        if not_patchable and (request_method() == 'PATCH'):
            self._error(field, "this field can not be changed with PATCH")

    def _validate_unique_combination(self, unique_combination, field, value):
        """ Custom validation if some fields are only unique in combination,
        e.g. user with id 1 can have several eventsignups for different events,
        but only 1 eventsignup for event with id 42
        unique_combination should be a list: The first item in the list is the
        resource. This is not pretty but necessary to make the validator work
        for different resources
        Alle other arguments are the fields
        Note: Make sure that other fields actually exists (setting them to
        required etc)
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
        not zero. In this case there is no signup
        Furthermore checks if time is in the singup window for the event.
        At last check if the event requires additional fields and display error
        if they are not present
        (Does nothing if signup_possible is set to False)
        """
        if signup_possible:
            lookup = {'_id': value}
            event = get_document('events', False, **lookup)

            if event:
                if (event['spots'] == 0):
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
        """ Makes sure that the user is anonymous. If you use this validator,
        ensure that there is a field 'user_id' in the same resource, e.g. by
        setting a dependancy
        (Does nothing if set to false
        """
        if only_anonymous:
            if not(self.document['user_id'] == -1):
                self._error(field, "This field can only be set for anonymous "
                            "users with user_id -1")

    def _validate_public_check(self, public_check, field, value):
        """ Validates the following:
        -1 only allowed if event in event_id
        random id only allowed for the user itself or resource admins
        """
        if not public_check:
            return
        if value == -1:
            lookup = {'id': self.document['event_id']}
            event = get_document('events', False, **lookup)
            if not(event):
                self._error(field, "Can only be -1 for public events. Event "
                            "with id %s can't be found." % self
                            .document['event_id'])

            elif not(event['is_public']):
                self._error(field, "Can only be -1 if event is public events. "
                            "Event with id %s is not public" % self
                            .document['event_id'])
        elif not(g.resource_admin or (g.logged_in_user == value)):
            self._error(field, "Given your access rights, only your own "
                        "user_id can be entered here")


"""
    Hooks to validate data before requests are performed
    First we have generic hooks to intercept requests and call validation
    functions, then we define those validation functions.
"""

resources_with_extra_checks = ['forwardusers',
                               'events']


def pre_insert_check(resource, items):
    """
    general function to call the custom logic validation
    :param resource: The resource we try to find a hook for, comes from eve
    :param items: the request-content as a list of dicts
    """
    if resource in resources_with_extra_checks:
        for doc in items:
            # the check-functions are the actual hooks testing the requests
            # of logical mistakes and everything else zerberus does not do
            eval("check_%s" % resource)(doc)


def pre_update_check(resource, updates, original):
    """
    general function to call the custom logic validation"""
    if resource in resources_with_extra_checks:
        data = original.copy()
        data.update(updates)
        eval("check_%s" % resource)(data)


def pre_replace_check(resource, document, original):
    """
    general function to call the custom logic validation"""
    if resource in resources_with_extra_checks:
        eval("check_%s" % resource)(document)


#
# /forwardusers
#


def check_forwardusers(data):
    """
    Checks whether a user is allowed to enroll for the given forward
    """
    db = app.data.driver.session

    forwardid = data.get('forward_id')
    forward = db.query(models.Forward).get(forwardid)

    # Users may only self enroll for public forwards
    if (not forward.is_public and not
            g.resource_admin and not
            g.logged_in_user == forward.owner_id):
        abort(403, description=debug_error_message(
            'You are not allowed to self enroll for this forward'
        ))

#
# /events
#


def check_events(data):
    """if we have no spots specified, this meens there is no registration
    window. Otherwise check for correct time-window."""
    if data.get('spots', -2) >= 0:
        if 'time_register_start' not in data or \
                'time_register_end' not in data:
            abort(422, description=(
                'You need to set time_register_start and time_register_end'
            ))
        elif data['time_register_end'] <= data['time_register_start']:
            abort(422, description=(
                'time_register_start needs to be before time_register_end'
            ))

    # check for correct times
    if data.get('time_start', dt.datetime.now()) > data.get('time_end',
                                                            dt.datetime.max):
        abort(422, description=(
            'time_end needs to be after time_start'
        ))
