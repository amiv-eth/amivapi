from flask import current_app as app
from flask import abort
from eve.utils import debug_error_message

import datetime as dt
import json

from amivapi import models, utils, confirm

resources_hooked = ['events', 'eventsignups', 'permissions']


def pre_insert_callback(resource, items):
    if resource in resources_hooked:
        for doc in items:
            eval("check_%s" % resource)(doc)


def pre_update_callback(resource, updates, original):
    print type(updates)
    print type(original)
    if resource in resources_hooked:
        data = original.copy()
        data.update(updates)
        eval("check_%s" % resource)(data)


""" /signups """


def check_eventsignups(data):
    db = app.data.driver.session

    eventid = data.get('event_id')
    event = db.query(models.Event).get(eventid)

    """check for available places"""
    if event.spots > 0:
        goneSpots = db.query(models.EventSignup).filter(
            models.EventSignup.event_id == eventid
        ).count()
        if goneSpots >= event.spots:
            abort(422, description=debug_error_message(
                'There are no spots left for event %d' % eventid
            ))
    if event.spots == -1:
        abort(422, description=(
            'Event %d does not offer a signup.' % eventid
        ))

    """check for correct signup time"""
    now = dt.datetime.now().isoformat()
    if event.spots >= 0:
        if now < event.time_register_start:
            abort(422, description=(
                'The signup for event %d is not open yet.' % eventid
            ))
        if now > event.time_register_end:
            abort(422, description=(
                'The signup for event %d is closed.' % eventid
            ))

    if data.get('user_id') == -1:
        if event.is_public is False:
            abort(422, description=debug_error_message(
                'The event is only open for registered users.'
            ))
        email = data.get('email')
        if email is None:
            abort(422, description=debug_error_message(
                'You need to provide an email-address or a valid user_id'
            ))
        alreadysignedup = db.query(models.EventSignup).filter(
            models.EventSignup.event_id == eventid,
            models.EventSignup.user_id == -1,
            models.EventSignup.email == email
        ).first() is not None
    else:
        userid = data.get('user_id')
        alreadysignedup = db.query(models.EventSignup).filter(
            models.EventSignup.event_id == eventid,
            models.EventSignup.user_id == userid
        ).first() is not None
    if alreadysignedup:
        abort(422, description=debug_error_message(
            'You are already signed up for this event, try to use PATCH'
        ))
    if 'extra_data' in data:
        data['extra_data'] = json.dumps(data.get('extra_data'))


def update_signups_schema(data):
    """
    validate the schema of extra_data"""
    db = app.data.driver.session
    eventid = data.get('event_id')
    event = db.query(models.Event).get(eventid)
    extraSchema = event.additional_fields
    if extraSchema is not None:
        resource_def = app.config['DOMAIN']['eventsignups']
        resource_def['schema'].update({
            'extra_data': {
                'type': 'dict',
                'schema': json.loads(extraSchema),
                'required': True,
            }
        })
        if data.get('extra_data') is None:
            abort(422, description=debug_error_message(
                'event %d requires extra data: %s' % (eventid, extraSchema)
            ))
    else:
        resource_def = app.config['DOMAIN']['eventsignups']
        resource_def['schema'].update({
            'extra_data': {
                'required': False,
            }
        })


def pre_signups_post_callback(request):
    update_signups_schema(utils.parse_data(request))


def signups_confirm_anonymous(items):
    """
    need an extra hook because we want to delete the item from items"""
    for doc in items:
        if doc['user_id'] == -1:
            confirm.confirm_actions(
                ressource='eventsignups',
                method='POST',
                doc=doc,
                items=items,
                email_field='email',
            )


def post_signups_post_callback(request, payload):
    """
    informs the user that an email with confirmation token was sent"""
    data = utils.parse_data(request)
    if data.get('user_id') == -1:
        confirm.return_status(payload)


def pre_signups_patch_callback(request, lookup):
    """
    don't allow PATCH on user_id, event_id or email"""
    data = utils.parse_data(request)
    if ('user_id' in data) or ('event_id' in data) or ('email' in data):
        abort(403, description=(
            'You only can change extra_data'
        ))
    update_signups_schema(utils.parse_data(request))


""" /events """


def check_events(data):
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
    if data.get('time_start', '0') > data.get(
            'time_end',
            dt.datetime.max.strftime('%Y-%m-%dT%H:%M:%SZ')):
        abort(422, description=(
            'time_end needs to be after time_start'
        ))


""" /permissions """


def check_permissions(data):
    now = dt.datetime.now()
    if data.get('expiry_date') < now.isoformat():
        abort(422, description=debug_error_message(
            'expiry_date needs to be in the future'
        ))


""" /forwardaddresses """


def pre_forwardaddresses_insert_callback(items):
    for doc in items:
        confirm.confirm_actions(
            ressource='forwardaddresses',
            method='POST',
            doc=doc,
            items=items,
            email_field='address',
        )


def post_forwardaddresses_post_callback(request, payload):
    """
    informs the user that an email with confirmation token was sent"""
    confirm.return_status(payload)


def pre_forwardaddresses_patch_callback(request, lookup):
    """
    don't allow to change forward_id"""
    data = utils.parse_data(request)
    if 'forward_id' in data:
        abort(403, description=(
            'You are not allowed to change the forward_id'
        ))
