"""
    amivapi.validation
    ~~~~~~~~~~~~~~~~~~~~~~~
    This extends the currently used validator to accept 'media' type

    Also adds hooks to validate other input
"""

import datetime as dt
import json

from flask import current_app as app
from flask import abort, g
from werkzeug.datastructures import FileStorage

from eve_sqlalchemy.validation import ValidatorSQL
from eve.methods.common import payload
from eve.validation import ValidationError
from eve.utils import debug_error_message, config

from amivapi import models


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


"""
    Hooks to validate data before requests are performed

    First we have generic hooks to intercept requests and call validation
    functions, then we define those validation functions.
"""


resources_with_extra_checks = ['forwardusers',
                               'events',
                               '_eventsignups',
                               'permissions']


def pre_insert_check(resource, items):
    """
    general function to call the custom logic validation

    :param resource: The resource we try to find a hook for, comes from eve
    :param items: the request-content as a list of dicts

    """
    if resource in resources_with_extra_checks:
        for doc in items:
            """the check-functions are the actual hooks testing the requests
            of logical mistakes and everything else zerberus does not do
            """
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


""" /forwardusers """


def check_forwardusers(data):
    """
    Checks whether a user is allowed to enroll for the given forward
    """
    db = app.data.driver.session

    forwardid = data.get('forward_id')
    forward = db.query(models.Forward).get(forwardid)

    """ Users may only self enroll for public forwards """
    if not forward.is_public and not g.resource_admin \
            and not g.logged_in_user == forward.owner_id:
        abort(403, description=debug_error_message(
            'You are not allowed to self enroll for this forward'
        ))


""" /eventsignups """


def check__eventsignups(data):
    db = app.data.driver.session

    eventid = data.get('event_id')
    event = db.query(models.Event).get(eventid)

    """check for available places"""
    if event.spots > 0:
        gone_spots = db.query(models._EventSignup).filter(
            models._EventSignup.event_id == eventid
        ).count()
        if gone_spots >= event.spots:
            abort(422, description=debug_error_message(
                'There are no spots left for event %d' % eventid
            ))
    if event.spots == -1:
        abort(422, description=(
            'Event %d does not offer a signup.' % eventid
        ))

    """check for correct signup time"""
    now = dt.datetime.now()
    if event.spots >= 0:
        if now < event.time_register_start:
            abort(422, description=(
                'The signup for event %d is not open yet.' % eventid
            ))
        if now > event.time_register_end:
            abort(422, description=(
                'The signup for event %d is closed.' % eventid
            ))

    """check if user is allowed to sign up for this event"""
    if data.get('user_id') == -1:
        """in this case we have an anonymous user who only provides an email"""
        if event.is_public is False:
            abort(422, description=debug_error_message(
                'The event is only open for registered users.'
            ))
        email = data.get('email')
        if email is None:
            abort(422, description=debug_error_message(
                'You need to provide an email-address or a valid user_id'
            ))
        alreadysignedup = db.query(models._EventSignup).filter(
            models._EventSignup.event_id == eventid,
            models._EventSignup.user_id == -1,
            models._EventSignup.email == email
        ).first() is not None
    else:
        """in this case the validator already checked that we have a valid
        user-id"""
        userid = data.get('user_id')
        alreadysignedup = db.query(models._EventSignup).filter(
            models._EventSignup.event_id == eventid,
            models._EventSignup.user_id == userid
        ).first() is not None

        """if the user did not provide an email, we just copy the address from
        the user-profile"""
        email = data.get('email')
        if email is None:
            data['email'] = db.query(models.User).get(userid).email

    if alreadysignedup:
        abort(422, description=debug_error_message(
            'You are already signed up for this event, try to use PATCH'
        ))

    """the extra-data got already checked by the validator and our
    pre_<request>-hooks below"""
    if 'extra_data' in data:
        data['extra_data'] = json.dumps(data.get('extra_data'))


""" /events """


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

    """check for correct times"""
    if data.get('time_start', dt.datetime.now()) > data.get('time_end',
                                                            dt.datetime.max):
        abort(422, description=(
            'time_end needs to be after time_start'
        ))

    """check if price is correct formatted"""
    if data.get('price', 0) < 0:
        abort(422, description=(
            'price needs to be positive or zero'
        ))

    """now we validate the zerberus-schema given in 'additional_fields' with
    zerberus"""
    validator = app.validator('', '')
    try:
        schema = json.loads(data.get('additional_fields'))
        validator.validate_schema(schema)
    except ValidationError as e:
            abort(422, description=(
                'validation exception: %s' % str(e)
            ))
    except Exception as e:
        # most likely a problem with the incoming payload, report back to
        # the client as if it was a validation issue
        abort(422, description=(
            'exception for additional_fields: %s' % str(e)
        ))


""" /permissions """


def check_permissions(data):
    if data.get('expiry_date') < dt.datetime.now():
        abort(422, description=debug_error_message(
            'expiry_date needs to be in the future'
        ))


"""
    Hooks to modify the schema for additional_fields of events
"""


def pre_signups_post_callback(request):
    update_signups_schema(payload())


def pre_signups_post(request):
    """
    the event may require to fill in additional fields, as specified in
    event.additional_fields. Therefore we need to update the schema the
    validator uses to check the signup-data.
    same for PUT, UPDATE and PATCH
    """
    update_signups_schema(payload())


def pre_signups_put(request, lookup):
    update_signups_schema(payload())


def pre_signups_update(request, lookup):
    update_signups_schema(payload())


def pre_signups_patch(request, lookup):
    """
    don't allow PATCH on user_id, event_id or email"""
    data = payload()
    if ('user_id' in data) or ('event_id' in data) or ('email' in data):
        abort(403, description=(
            'You only can change extra_data'
        ))
    """
    the event may require to fill in additional fields, as specified in
    event.additional_fields. Therefore we need to update the schema the
    validator uses to check the signup-data.
    """
    update_signups_schema(payload())


# TODO(Conrad to Hermann): What is the purpose of this function?
# Function name says update, comment says validate... what?
def update_signups_schema(data):
    """
    validate the schema of extra_data
    """
    db = app.data.driver.session
    eventid = data.get('event_id')
    event = db.query(models.Event).get(eventid)
    if event is not None:
        """we need to check this because the validator did not run yet"""

        extra_schema = event.additional_fields
        if extra_schema is not None:
            resource_def = config.DOMAIN['_eventsignups']
            resource_def['schema'].update({
                'extra_data': {
                    'type': 'dict',
                    'schema': json.loads(extra_schema),
                    'required': True,
                }
            })
            if data.get('extra_data') is None:
                abort(422, description=debug_error_message(
                    'event %d requires extra data: %s' % (eventid,
                                                          extra_schema)
                ))
        else:
            resource_def = config.DOMAIN['_eventsignups']
            resource_def['schema'].update({
                'extra_data': {
                    'required': False,
                }
            })
