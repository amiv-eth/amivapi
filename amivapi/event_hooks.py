from flask import current_app as app
from flask import abort
from eve.utils import debug_error_message

import datetime as dt

from amivapi import models


def pre_users_get_callback(request, lookup):
    print('A GET request on the users endpoint has just been received!')


def post_users_get_callback(request, lookup):
    print('The GET request on the users endpoint has just been handled')


def pre_signups_post_callback(request):
    #for the moment we only support json formatted data
    data = request.get_json()
    if data.get('user_id') == -1:
        eventid = data.get('event_id')
        db = app.data.driver.session
        event = db.query(models.Event).get(eventid)
        if event is None:
            abort(422, description=debug_error_message(
                'The given event_id could not be found in /events'
            ))
        if event.is_public is False:
            abort(422, description=debug_error_message(
                'The event is only open for registered users.'
            ))
        if data.get('email') is None:
            abort(422, description=debug_error_message(
                'You need to provide an email-address or a valid user_id'
            ))
    elif data.get('email') is None:
        userid = data.get('user_id')
        db = app.data.driver.session
        user = db.query(models.User).get(userid)
        if user is None:
            abort(422, description=debug_error_message(
                'The given user_id could not be found in /users'
            ))
        data['email'] = user.email
        print "added %s to signup of user %d" % (user.email, userid)


def pre_groupmembership_post_callback(request):
    data = request.get_json()
    now = dt.datetime.now()
    if data.get('expiry_date') < now.isoformat():
        abort(422, description=debug_error_message(
            'expiry_date needs to be in the future'
        ))
