from flask import current_app as app
from flask import abort
from eve.utils import debug_error_message

from amivapi import models


def pre_users_get_callback(request, lookup):
    print('A GET request on the users endpoint has just been received!')


def post_users_get_callback(request, lookup):
    print('The GET request on the users endpoint has just been handled')


def pre_signups_post_callback(request):
    #for the moment we only support json formatted data
    data = request.get_json()
    if data.get('email') is None and data.get('user_id') == -1:
        abort(422, description=debug_error_message(
            'You need to provide an email or a valid user_id'
        ))
    if data.get('email') is None and data.get('user_id') != -1:
        userid = data.get('user_id')
        db = app.data.driver.session
        user = db.query(models.User).get(userid)
        if user is None:
            abort(422, description=debug_error_message(
                'The user could not be found'
            ))
        data['email'] = user.email
        print "added %s to signup of user %d" % (user.email, userid)
