from flask import current_app as app
from amivapi import models


def pre_users_get_callback(request, lookup):
    print('A GET request on the users endpoint has just been received!')


def post_users_get_callback(request, lookup):
    print('The GET request on the users endpoint has just been handled')


def pre_signups_post_callback(request):
    if request.form['email'] == "" and request.form['userid'] != -1:
        userid = request.form['user_id']
        db = app.data.driver.session
        email = db.query(models.User).get(userid).email
        request.form['email'] = email
    return request
