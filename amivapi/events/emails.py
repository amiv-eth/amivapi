# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Email formatting.

Needed when users are notified about their event signups.
"""
from flask import current_app, url_for
from itsdangerous import URLSafeSerializer

from amivapi.events.utils import get_token_secret
from amivapi.utils import mail


def find_reply_to_email(event):
    """Get the moderator or default event mailing reply-to email address."""
    id_field = current_app.config['ID_FIELD']

    if event['moderator'] is not None:
        lookup = {id_field: event['moderator']}
        moderator = current_app.data.find_one('users', None, **lookup)

        if moderator is not None:
            return moderator['email']

    return current_app.config.get('DEFAULT_EVENT_REPLY_TO')


def notify_signup_accepted(event, signup, waiting_list=False):
    """Send an email to a user that his signup was accepted"""
    id_field = current_app.config['ID_FIELD']

    if signup.get('user'):
        lookup = {id_field: signup['user']}
        user = current_app.data.find_one('users', None, **lookup)
        name = user['firstname']
        email = user['email']
    else:
        name = 'Guest of AMIV'
        email = signup['email']

    s = URLSafeSerializer(get_token_secret())
    token = s.dumps(str(signup[id_field]))

    if current_app.config.get('SERVER_NAME') is None:
        current_app.logger.warning("SERVER_NAME is not set. E-Mail links "
                                   "will not work!")

    deletion_link = url_for('emails.on_delete_signup', token=token,
                            _external=True)
    event_name = event.get('title_en') or event.get('title_de')

    reply_to_email = find_reply_to_email(event)

    if waiting_list:
        mail([email],
             'Your signup for %s was put on the waiting list' % event_name,
             current_app.config['WAITING_LIST_EMAIL_TEXT'].format(
                name=name,
                title=event_name),
             reply_to_email)
    else:
        mail([email],
             'Your event signup for %s was accepted' % event_name,
             current_app.config['ACCEPT_EMAIL_TEXT'].format(
                name=name,
                title=event_name,
                link=deletion_link,
                deadline=event['time_register_end'].strftime('%H.%M %d.%m.%Y')),
             reply_to_email)


def notify_signup_deleted(signup):
    """Send an email to a user that his signup was deleted"""
    id_field = current_app.config['ID_FIELD']

    if signup.get('user'):
        lookup = {id_field: signup['user']}
        user = current_app.data.find_one('users', None, **lookup)
        if user is None:  # User was deleted
            return
        name = user['firstname']
        email = user['email']
    else:
        name = 'Guest of AMIV'
        email = signup['email']

    event = current_app.data.find_one(
        'events', None,
        **{current_app.config['ID_FIELD']: signup['event']})

    if current_app.config.get('SERVER_NAME') is None:
        current_app.logger.warning("SERVER_NAME is not set. E-Mail links "
                                   "will not work!")

    reply_to_email = find_reply_to_email(event)

    mail([email],
         'Successfully deregistered from %s' % event.get(
             'title_en') or event.get('title_de'),
         current_app.config['DEREGISTER_EMAIL_TEXT'].format(
            name=name,
            title=event.get('title_en') or event.get('title_de')),
         reply_to_email)


def send_confirmmail_to_unregistered_users(items):
    """Send a confirmation email for external signups(email only)

    Args:
        item: The item, which was just inserted into the database
    """
    for item in items:
        if item.get('user') is None:
            event = current_app.data.find_one(
                'events', None,
                **{current_app.config['ID_FIELD']: item['event']})

            title = event.get('title_en') or event.get('title_de')

            s = URLSafeSerializer(get_token_secret())
            token = s.dumps(str(item['_id']))

            if current_app.config.get('SERVER_NAME') is None:
                current_app.logger.warning("SERVER_NAME is not set. E-Mail "
                                           "links will not work!")

            confirm_link = url_for('emails.on_confirm_email', token=token,
                                   _external=True)

            reply_to_email = find_reply_to_email(event)

            mail([item['email']],
                 'Registration for %s' % title,
                 current_app.config['CONFIRM_EMAIL_TEXT'].format(
                     title=title,
                     link=confirm_link),
                 reply_to_email)
