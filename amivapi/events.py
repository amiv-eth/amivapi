# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Everything related to events.

Models for Events, and EventSignups, functions to handle confirmation mails.
Be sure to call ``init_app`` to initialize
"""
from datetime import datetime
import json

from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
    Unicode,
    UnicodeText,
    Text,
    Boolean,
    Integer,
    CHAR)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from flask import current_app as app
from flask import Blueprint, request, abort, g

from eve.methods.post import post
from eve.render import send_response
from eve.methods.common import payload
from eve.utils import config, request_method
from eve.validation import SchemaError

from amivapi.authorization import common_authorization
from amivapi import models, utils
from amivapi.db_utils import Base

eventdomain = {}
"""Collect event related domains."""


class Event(Base):
    """Event model."""

    __description__ = {
        'general': "An Event is basically everything happening in the AMIV. "
        "All time fields have the format YYYY-MM-DDThh:mmZ, e.g. "
        "2014-12-20T11:50:06Z",
        'methods': {
            'GET': "You are always allowed, even without session, to view "
            "AMIV-Events"
        },
        'fields': {
            'price': 'Price of the event as Integer in Rappen.',
            'additional_fields': "must be provided in form of a JSON-Schema. "
            "You can add here fields you want to know from people signing up "
            "going further than their email-address",
            'allow_email_signup': "If False, only AMIV-Members can sign up "
            "for this event",
            'spots': "For no limit, set to '0'. If no signup required, set to "
            "'-1'. Otherwise just provide an integer.",
        }
    }
    __expose__ = True
    __projected_fields__ = ['signups']

    __public_methods__ = ['GET']

    time_start = Column(DateTime)
    time_end = Column(DateTime)
    location = Column(Unicode(50))
    allow_email_signup = Column(Boolean, default=False, nullable=False)
    price = Column(Integer)  # Price in Rappen
    spots = Column(Integer, nullable=False)
    time_register_start = Column(DateTime)
    time_register_end = Column(DateTime)
    additional_fields = Column(Text)
    show_infoscreen = Column(Boolean, default=False)
    show_website = Column(Boolean, default=False)
    show_announce = Column(Boolean, default=False)

    @hybrid_property
    def signup_count(self):
        """Get number of signups."""
        return len(self.signups)

    # Images
    img_thumbnail = Column(CHAR(100))
    img_banner = Column(CHAR(100))
    img_poster = Column(CHAR(100))
    img_infoscreen = Column(CHAR(100))

    title_de = Column(UnicodeText)
    title_en = Column(UnicodeText)
    description_de = Column(UnicodeText)
    description_en = Column(UnicodeText)
    catchphrase_de = Column(UnicodeText)
    catchphrase_en = Column(UnicodeText)

    # relationships
    signups = relationship("EventSignup", backref="event",
                           cascade="all")


class EventSignup(Base):
    """Model for a signup."""

    __description__ = {
        'general': "You can signup here for an existing event inside of the "
        "registration-window. External Users can only sign up to public "
        "events.",
        'fields': {
            'additional_fields': "Data-schema depends on 'additional_fields' "
            "from the mapped event. Please provide in json-format.",
            'user_id': "To sign up as external user, set 'user_id' to '-1'",
            'email': "For registered users, this is just a projection of your "
            "general email-address. External users need to provide their email"
            " here.",
        }}
    __expose__ = True
    __projected_fields__ = ['event', 'user']

    __owner__ = ['user_id']
    __owner_methods__ = ['GET', 'PATCH', 'DELETE']
    __registered_methods__ = ['POST']

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(CHAR(100), ForeignKey("users.email"))
    additional_fields = Column(Text)

    """for unregistered users"""
    _email_unreg = Column(Unicode(100))
    _token = Column(CHAR(20), unique=True, nullable=True)
    _confirmed = Column(Boolean, default=False)

confirmprint = Blueprint('confirm', __name__)
documentation = {}

# Create and update schemas
# Has to happen after both class definitions or the relationship in events
# cannot be evaluated (needed in make_domain)

eventdomain.update(utils.make_domain(Event))
eventdomain.update(utils.make_domain(EventSignup))

# additional validation
eventdomain['events']['schema']['additional_fields'].update({
    'type': 'json_schema'})
eventdomain['events']['schema']['price'].update({'min': 0})
eventdomain['events']['schema']['spots'].update({
    'min': -1,
    'if_this_then': ['time_register_start', 'time_register_end']})
eventdomain['events']['schema']['time_register_end'].update({
    'dependencies': ['time_register_start'],
    'later_than': 'time_register_start'})
eventdomain['events']['schema']['time_end'].update({
    'dependencies': ['time_start'],
    'later_than': 'time_start'})

# time_end for /events requires time_start
eventdomain['events']['schema']['time_end'].update({
    'dependencies': ['time_start']
})

# event images
eventdomain['events']['schema'].update({
    'img_thumbnail': {'type': 'media', 'filetype': ['png', 'jpeg']},
    'img_banner': {'type': 'media', 'filetype': ['png', 'jpeg']},
    'img_poster': {'type': 'media', 'filetype': ['png', 'jpeg']},
    'img_infoscreen': {'type': 'media', 'filetype': ['png', 'jpeg']}
})

# POST done by custom endpoint
eventdomain['eventsignups']['resource_methods'] = ['GET']

# schema extensions including custom validation
eventdomain['eventsignups']['schema']['event_id'].update({
    'not_patchable': True,
    'unique_combination': ['user_id', 'email'],
    'signup_requirements': True})
eventdomain['eventsignups']['schema']['user_id'].update({
    'not_patchable': True,
    'unique_combination': ['event_id'],
    'only_self_enrollment_for_event': True})
eventdomain['eventsignups']['schema']['email'].update({
    'not_patchable': True,
    'unique_combination': ['event_id'],
    'only_anonymous': True,
    'email_signup_must_be_allowed': True,
    'regex': utils.EMAIL_REGEX})

# Since the data relation is not evaluated for posting, we need to remove
# it from the schema TODO: EXPLAIN BETTER
del(eventdomain['eventsignups']['schema']['email']['data_relation'])
# Remove _email_unreg and _token from the schema since they are only
# for internal use and should not be visible
del(eventdomain['eventsignups']['schema']['_email_unreg'])
del(eventdomain['eventsignups']['schema']['_token'])

eventdomain['eventsignups']['schema']['additional_fields'].update({
    'type': 'json_event_field'})


class EventValidator(object):
    """Custom Validator for event validation rules."""

    def _validate_type_json_schema(self, field, value):
        """Validate a cerberus schema saved as JSON.

        1.  Is it JSON?
        2.  Is it a valid cerberus schema?

        Args:
            field (string): field name.
            value: field value.
        """
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
        """Validate data in json format with event data.

        1.  Is it JSON?
        2.  Try to find event
        3.  Validate schema and get all errors with prefix 'additional_fields:'

        Args:
            field (string): field name.
            value: field value.
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
                lookup = {'id': self._original_document['event_id']}
            elif ('event_id' in self.document.keys()):
                lookup = {'id': self.document['event_id']}
            else:
                self._error(field, "Cannot evaluate additional fields " +
                                   "without event_id")
                return

            event = app.data.find_one('events', None, **lookup)

            # Load schema, we can use this without caution because only valid
            # json schemas can be written to the database
            if event is not None:
                schema = json.loads(event['additional_fields'])
                v = app.validator(schema)  # Create a new validator
                v.validate(data)

                # Move errors to main validator
                for key in v.errors.keys():
                    self._error("%s: %s" % (field, key), v.errors[key])

    def _validate_signup_requirements(self, signup_possible, field, value):
        """Validate if signup requirements are met.

        Used for an event_id field - checks if the value "spots" is
        not -1. In this case there is no signup.

        Furthermore checks if current time is in the singup window for the
        event.

        At last check if the event requires additional fields and display error
        if they are not present

        This will validate the additional fields with nothing as input to get
        errors as if additional_fields would be in the schema

        Args:
            singup_possible (bool); validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if signup_possible:
            event = app.data.find_one('events', None, id=value)

            if event:
                if (event['spots'] == -1):
                    self._error(field, "the event with id %s has no signup" %
                                value)
                else:
                    # The event has signup, check if it is open
                    now = datetime.utcnow()
                    if now < event['time_register_start']:
                        self._error(field, "the signup for event with %s is"
                                    "not open yet." % value)
                    elif now > event['time_register_end']:
                        self._error(field, "the signup for event with id %s"
                                    "closed." % value)

                # If additional fields is missing still call the validator,
                # except an emtpy string, then the valid
                if (event['additional_fields'] and
                        ('additional_fields' not in self.document.keys())):
                    # Use validator to get accurate errors
                    self._validate_type_json_event_field('additional_fields',
                                                         None)

    def _validate_only_self_enrollment_for_event(self, enabled, field, value):
        """Validate if the id can be used to enroll for an event.

        1.  -1 is a public id, anybody can use this (to e.g. sign up a friend
            via mail) (if public has to be determined somewhere else)
        2.  other id: Registered users can only enter their own id
        3.  Exception are resource_admins: they can sign up others as well

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            if not(g.resource_admin or (g.logged_in_user == value)):
                self._error(field, "You can only enroll yourself. (%s: "
                            "%s is yours)." % (field, g.logged_in_user))

    def _validate_email_signup_must_be_allowed(self, enabled, field, value):
        """Validation for a event_id field in eventsignups.

        Validates if the event allows self enrollment.

        Except event moderator and admins, they can ignore this

        Args:
            enabled (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if enabled:
            # Get event
            event_id = self.document.get('event_id', None)
            event = app.data.find_one("events", None, id=event_id)

            # If the event doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if event is not None and not(event["allow_email_signup"]):
                self._error(field,
                            "event with id '%s' does not allow signup with "
                            "email address." % event_id)

    def _validate_only_anonymous(self, only_anonymous, field, valie):
        """Make sure that the user is anonymous.

        If you use this validator, ensure that there is a field 'user_id' in
        the same resource, e.g. by setting a dependancy

        Args:
            only_anonymous (bool): validates nothing if set to false
            field (string): field name.
            value: field value.
        """
        if only_anonymous:
            if not(self.document.get('user_id', None) == -1):
                self._error(field, "This field can only be set for anonymous "
                            "users with user_id -1")

    def _validate_later_than(self, later_than, field, value):
        """Validate time dependecy.

        Value must be at the same time or later than a the value of later_than

        :param later_than: The field it will be compared to
        :param field: field name.
        :param value: field value.
        """
        if value < self.document[later_than]:
            self._error(field, "Must be at a point in time after %s" %
                        later_than)

    def _validate_if_this_then(self, if_this_then, field, value):
        """Validate integer condition.

        if value > 0, then other fields must exist

        Args:
            if_this_then (list): fields that are required if value > 0.
            field (string): field name.
            value: field value.
        """
        if value > 0:
            for item in if_this_then:
                if item not in self.document.keys():
                    self._error(item, "Required field.")


def send_confirmmail(resource, token, email):
    """Send mail. Not implemented.

    For the development-Version, we do not actually send emails but print
    the token. For testing, you will find the token in the database or copy it
    from the command-line
    :param resource: The resource of the current request as a string
    :param token: The token connected to the data-entry which needs
    confirmation
    :param email: address the email will be send to
    """
    print('email send with token %s to %s' % (token, email))


def confirm_actions(resource, email, items):
    """Create unique token needed for confirmation.

    This method will generate a random token and append it to items.
    For 'eventsignups', the email will be swapped to the key '_email_unreg'.
    An email will be send to the user for confirmation.
    :param resource: the ressource current as a string
    :param items: the dictionary of the data which will be inserted into the
    database
    :param email: The email the confirmation mail will be send to
    """
    token = utils.token_generator(size=20)
    send_confirmmail(resource, token, email)
    if resource == 'eventsignups':
        # email is no relation, move it to _email_unreg
        items.pop('email')
        items['_email_unreg'] = email
    items['_token'] = token


def change_status(response):
    """Change status to "accepted" for actions that need confirmation.

    This function changes the caught. response of a post. Eve returns 201
    because the data got just deleted out of the payload and the empty payload
    got handled correct, but we need to return 202 and a hint to confirm the
    email-address
    :param response: the response from eve, a list of 4 items
    :returns: new response with changed status-code
    """
    if response[3] in [201, 200] and 'id' not in response:
        """No items actually inserted but saved in Confirm,
        Send 202 Accepted"""
        response[0].update({'_issue': 'Please check your email and POST the '
                           'token to /confirms to process your request',
                            config.STATUS: 202})
        return response[0], None, None, 202
    return response


def route_post(resource, lookup, anonymous=True):
    """Post endpoint to be able to change status.

    This method maps the request to the corresponding eve-functions or
    implements own functions.
    Similar to eve.endpoint
    :param resource: the resource where the request comes from
    :param lookup: the lookup-dictionary like in the hooks
    :param anonymous: True if the request needs confirmation via email
    :returns: the response from eve, with correct status code
    """
    response = None
    common_authorization(resource, 'POST')
    response = post(resource)
    if anonymous:
        response = change_status(response)
    return send_response(resource, response)


documentation['eventsignups'] = {
    'general': "Signing up to an event is possible in two cases: Either you "
    "are a registered user ot you are not registered, but the event is "
    "public and you have an email-address.",
    'methods': {
        'GET': "You can onyl see your own signups unless you are an "
        "administrator",
        'POST': "If you are not registered, the signup becomes valid as you "
        "confirm your email-address"
    },
    'fields': {
        'additional fields': "Needs to provide all necessary data defined in "
        "event.additional_fields",
        'user_id': "If you are not registered, set this to -1"
    },
    'schema': 'eventsignups'
}


@confirmprint.route('/eventsignups', methods=['POST'])
def handle_eventsignups():
    """These are custom api-endpoints from the confirmprint Blueprint.

    We don't want eve to handle POST to /eventsignups because we need to
    change the status of the response
    :returns: eve-response with (if POST was correct) changed status-code
    """
    print("i am here am i?")
    data = payload()  # we only allow POST -> no error with payload()
    anonymous = (data.get('user_id') == -1)
    return route_post('eventsignups', data, anonymous)


@confirmprint.route('/confirmations', methods=['POST'])
def on_post_token():
    """Confirmation token endpoint.

    :returns: 201 if token correct
    """
    data = payload()
    return execute_confirmed_action(data.get('token'))


def execute_confirmed_action(token):
    """Do whatever needed confirmation.

    from a given token, this function will search for a stored action in
    Confirms and send it to eve's post_internal
    PATCH and PUT are not implemented yet
    :param token: the Token which was send to an email-address for confirmation
    :returns: 201 in eve-response-format, without confirmed data
    """
    db = app.data.driver.session
    signup = db.query(models.EventSignup).filter_by(_token=token).first()
    doc = signup
    if doc is None:
        abort(404, description=(
            'This token could not be found.'
        ))
    resource = doc.__tablename__
    # response = patch_internal(resource, {'_confirmed': True}, False,
    #                        False, _id=doc._id)
    doc._confirmed = True
    db.flush()
    response = [{}, None, None, 201]
    # app.data.update(resource, doc._id, {'_confirmed': True})
    return send_response(resource, response)


def signups_confirm_anonymous(items):
    """Hook to confirm external signups."""
    for doc in items:
        if doc['user_id'] == -1:
            doc['_confirmed'] = False
            confirm_actions('eventsignups', doc['email'], doc)
        else:
            doc['_confirmed'] = True


def needs_confirmation(resource, doc):
    """Check if confirmation is needed."""
    return (resource == 'eventsignups' and
            doc.get('_email_unreg') is not None)


def pre_delete_confirmation(resource, original):
    """Hook to check if confirmation is needed."""
    if needs_confirmation(resource, original):
        token_authorization(resource, original)


def pre_update_confirmation(resource, updates, original):
    """Hook to check if confirmation is needed."""
    pre_delete_confirmation(resource, original)


def pre_replace_confirmation(resource, document, original):
    """Hook to check if confirmation is needed."""
    pre_delete_confirmation(resource, original)


def token_authorization(resource, original):
    """Check confirmation token.

    checks if a request to an item-endpoint is authorized by the correct Token
    in the header
    Will abort if Token is incorrect.
    :param resourse: the resource of the item as a string
    :param original: The original data of the item which is requested
    """
    token = request.headers.get('Token')
    model = utils.get_class_for_resource(models, resource)
    is_owner = g.logged_in_user in utils.get_owner(model, original['id'])
    if is_owner:
        print("Access to %s/%d granted for owner %d without token" % (
            resource, original['id'], g.logged_in_user))
        return
    if g.resource_admin:
        print("Access to %s/%d granted for admin %d without token" % (
            resource, original['id'], g.logged_in_user))
        return
    if token is None:
        # consistent with _etag
        abort(403, description="Please provide a valid token.")
    if token != original['_token']:
        # consistent with _etag
        abort(412, description="Token for external user not valid.")


# Remove fields _email_unreg and _token
def _replace(item, old_key, new_key):
    if item.get(old_key):
        item[new_key] = item.pop(old_key)


# Hooks for input
def replace_email_insert(items):
    """List of inserted items."""
    for item in items:
        _replace(item, 'email', '_email_unreg')


def replace_email_replace(item, original):
    """One item."""
    _replace(item, 'email', '_email_unreg')


def replace_email_update(updates, original):
    """One item."""
    _replace(updates, 'email', '_email_unreg')


# Hooks for output
def replace_email_fetched_item(response):
    """The response will contain exactly one item."""
    _replace(response, '_email_unreg', 'email')


def replace_email_fetched_resource(response):
    """The response will be a dict, the list of items is in '_items'."""
    for item in response['_items']:
        _replace(item, '_email_unreg', 'email')


def replace_email_replaced(item, original):
    """The response will be a dict, the list of items is in '_items'."""
    _replace(item, '_email_unreg', 'email')


def replace_email_inserted(items):
    """List of inserted items."""
    for item in items:
        _replace(item, '_email_unreg', 'email')


def replace_email_updated(updates, original):
    """One updated item."""
    _replace(updates, '_email_unreg', 'email')


# Hooks to remove '_token' from output after db access
def remove_token_fetched_item(response):
    """The response will contain exactly one item."""
    del(response['_token'])


def remove_token_fetched_resource(response):
    """Response will be a dict, the list of items is in '_items'."""
    for item in response['_items']:
        item.pop('_token', None)


def remove_token_replaced(item, original):
    """Response will be a dict, the list of items is in '_items'."""
    item.pop('_token', None)


def remove_token_inserted(items):
    """List of inserted items."""
    for item in items:
        item.pop('_token', None)


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    utils.register_domain(app, eventdomain)
    utils.register_validator(app, EventValidator)

    app.register_blueprint(confirmprint)

    # Hooks to move 'email' to '_unregistered_email' after db access
    app.on_insert_eventsignups += replace_email_insert
    app.on_update_eventsignups += replace_email_update
    app.on_replace_eventsignups += replace_email_replace

    # Hooks to move '_unregistered_email' to 'email' after db access
    app.on_inserted_eventsignups += replace_email_inserted
    app.on_fetched_item_eventsignups += replace_email_fetched_item
    app.on_fetched_resource_eventsignups += replace_email_fetched_resource
    app.on_replaced_eventsignups += replace_email_replaced
    app.on_updated_eventsignups += replace_email_updated

    # Hooks to remove tokens from output
    app.on_inserted_eventsignups += remove_token_inserted
    app.on_fetched_item_eventsignups += remove_token_fetched_item
    app.on_fetched_resource_eventsignups += remove_token_fetched_resource
    app.on_replaced_eventsignups += remove_token_replaced
