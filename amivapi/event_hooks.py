from flask import current_app as app
from flask import abort, g
from eve.utils import debug_error_message
from eve.validation import ValidationError
from eve.methods.common import payload

import datetime as dt
import json

from amivapi import models, confirm

resources_hooked = ['forwardusers', 'events', '_eventsignups', 'permissions']


def pre_insert_check(resource, items):
    """
    general function to call the custom logic validation

    :param resource: The resource we try to find a hook for, comes from eve
    :param items: the request-content as a list of dicts

    """
    if resource in resources_hooked:
        for doc in items:
            """the check-functions are the actual hooks testing the requests
            of logical mistakes and everything else zerberus does not do
            """
            eval("check_%s" % resource)(doc)


def pre_update_check(resource, updates, original):
    """
    general function to call the custom logic validation"""
    if resource in resources_hooked:
        data = original.copy()
        data.update(updates)
        eval("check_%s" % resource)(data)


def pre_replace_check(resource, document, original):
    """
    general function to call the custom logic validation"""
    if resource in resources_hooked:
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
            resource_def = app.config['DOMAIN']['_eventsignups']
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
            resource_def = app.config['DOMAIN']['_eventsignups']
            resource_def['schema'].update({
                'extra_data': {
                    'required': False,
                }
            })


def pre_signups_post_callback(request):
    update_signups_schema(payload())


def signups_confirm_anonymous(items):
    """
    hook to confirm external signups
    """
    for doc in items:
        if doc['user_id'] == -1:
            if not confirm.confirm_actions(
                resource='_eventsignups',
                method='POST',
                doc=doc,
            ):
                items.remove(doc)


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


""" /forwardaddresses """


def forwardaddresses_insert_anonymous(items):
    for doc in items:
        if not confirm.confirm_actions(
            resource='_forwardaddresses',
            method='POST',
            doc=doc,
        ):
            items.remove(doc)


""" /users """


def pre_users_get(request, lookup):
    """ Prevent users from reading their password """
    projection = request.args.get('projection')
    if projection and 'password' in projection:
        abort(403, description='Bad projection field: password')


def pre_users_patch(request, lookup):
    """
    Don't allow a user to change fields
    """
    if g.resource_admin:
        return

    disallowed_fields = ['username', 'firstname', 'lastname', 'birthday',
                         'legi', 'nethz', 'department', 'phone',
                         'ldapAddress', 'gender', 'membership']

    data = payload()

    for f in disallowed_fields:
        if f in data:
            app.logger.debug("Rejecting patch due to insufficent priviledges"
                             + "to change " + f)
            abort(403, description=(
                'You are not allowed to change your ' + f
            ))


""" Hooks to add _author field to all database inserts """


def set_author_on_insert(resource, items):
    _author = getattr(g, 'logged_in_user', -1)
    for i in items:
        i['_author'] = _author


def set_author_on_replace(resource, item, original):
    set_author_on_insert(resource, [item])
