# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Email formatting.

Needed when users are notified about their event signups.
"""
from datetime import datetime, timezone
from flask import current_app, url_for
from itsdangerous import URLSafeSerializer

from amivapi.events.utils import get_token_secret
from amivapi.utils import mail_from_template, get_calendar_invite


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
    event_id = event[id_field]
    title_en = event['title_en']
    title_de = event['title_de']
    description_en = event['description_en']
    description_de = event['description_de']
    location = (event['location'] or '')
    time_start = event['time_start']
    time_end = event['time_end']
    time_now = datetime.now(timezone.utc)

    signup_additional_info_en = event['signup_additional_info_en']
    signup_additional_info_de = event['signup_additional_info_de']

    reply_to_email = find_reply_to_email(event)

    # Time is a required property for ics calendar events
    if time_start:
        calendar_invite = (
            get_calendar_invite('events_accepted_calendar_invite', dict(
                title_en=(title_en or title_de),
                event_id=event_id,
                time_start=time_start,
                time_end=time_end,
                time_now=time_now,
                description_en=(description_en or description_de or ''),
                reply_to_email=reply_to_email,
                location=location,
                signup_additional_info_en=(signup_additional_info_en or
                                           signup_additional_info_de or
                                           ''),
            )))
    else:
        calendar_invite = None

    if waiting_list:
        mail_from_template(
            to=[email],
            subject='Your signup for %s was put on the waiting list'
                    % (title_en or title_de),
            template_name='events_waitingList',
            template_args=dict(
                name=name,
                title_en=(title_en or title_de),
                title_de=(title_de or title_en)),
            reply_to=reply_to_email)
    else:
        mail_from_template(
            to=[email],
            subject='Your event signup for %s was accepted'
                    % (title_en or title_de),
            template_name='events_accept',
            template_args=dict(
                name=name,
                title_en=(title_en or title_de),
                title_de=(title_de or title_en),
                link=deletion_link,
                signup_additional_info_en=(signup_additional_info_en or
                                           signup_additional_info_de),
                signup_additional_info_de=(signup_additional_info_de or
                                           signup_additional_info_en),
                deadline=event['time_deregister_end']),
            reply_to=reply_to_email,
            calendar_invite=calendar_invite)


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

    title_en = event.get('title_en')
    title_de = event.get('title_de')

    reply_to_email = find_reply_to_email(event)

    mail_from_template(
        to=[email],
        subject='Successfully deregistered from %s' % (title_en or title_de),
        template_name='events_deregister',
        template_args=dict(
            name=name,
            title_en=(title_en or title_de),
            title_de=(title_de or title_en)),
        reply_to=reply_to_email)


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

            title_en = event.get('title_en')
            title_de = event.get('title_de')

            s = URLSafeSerializer(get_token_secret())
            token = s.dumps(str(item['_id']))

            if current_app.config.get('SERVER_NAME') is None:
                current_app.logger.warning("SERVER_NAME is not set. E-Mail "
                                           "links will not work!")

            confirm_link = url_for('emails.on_confirm_email', token=token,
                                   _external=True)

            reply_to_email = find_reply_to_email(event)

            mail_from_template(
                to=[item['email']],
                subject='Registration for %s' % (title_en or title_de),
                template_name='events_confirm',
                template_args=dict(
                    title_en=(title_en or title_de),
                    title_de=(title_de or title_en),
                    link=confirm_link),
                reply_to=reply_to_email)
