# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Api group resources.

Contains groups, groupmemberships, groupaddresses and forwards as well as
group permission and mailinglist functions.
"""

from os import remove, rename
import jsonschema

from sqlalchemy import (
    Column,
    ForeignKey,
    Unicode,
    Integer,
    Boolean)
from sqlalchemy.orm import relationship

from flask import g, current_app as app
from flask import abort

from eve.utils import config

from amivapi.utils import (
    get_owner,
    get_class_for_resource,
    EMAIL_REGEX,
    make_domain,
    register_domain,
    register_validator,
    Base,
    JSONText
)
from amivapi.models import User


class Group(Base):
    """Group model."""

    __description__ = {
        'general': "This resource describes the different teams in AMIV."
        "A group can grant API permissions and can be reached with several "
        "addresses. To see the addresses of this group, see /groupaddresses"
        "To see the members, have a look at '/groupmembers'. "
        "To see the addresses messages are forwarded to, see /groupforwards",
        'fields': {
            'allow_self_enrollment': "If true, the group can be seen by all "
            "users and they can subscribe themselves",
            'has_zoidberg_share': "Wether the group has a share in the amiv "
            "storage",
            "permissions": "permissions the group grants. has to be according "
            "to the jsonschema available at /notyetavailable"  # TODO!
        }}
    __expose__ = True
    __projected_fields__ = ['members', 'addresses', 'forwards']
    __embedded_fields__ = ['members', 'addresses', 'forwards']

    __owner__ = ['moderator_id', 'members.user_id']
    __owner_methods__ = ['GET']  # Only admins can modify the group itself!

    __registered_methods__ = ['GET']  # All users can check for open groups

    name = Column(Unicode(100), unique=True, nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allow_self_enrollment = Column(Boolean, default=False, nullable=False)

    has_zoidberg_share = Column(Boolean, default=False, nullable=False)

    permissions = Column(JSONText)

    owner = relationship(User, foreign_keys=moderator_id)

    members = relationship("GroupMember", backref="group", cascade="all")
    addresses = relationship("GroupAddress", backref="group", cascade="all")
    forwards = relationship("GroupForward", backref="group", cascade="all")


class GroupAddress(Base):
    """Group address model."""

    __description__ = {
        'general': "An email address associated with a group. By adding "
        "an address here, all mails sent to that address will be forwarded "
        "to all members and forwards of the associated group.",
        'fields': {
            'email': "E-Mail address for the group",
        }
    }
    __expose__ = True
    __projected_fields__ = ['group']

    __owner__ = ["group.moderator_id"]
    __owner_methods__ = ['GET', 'DELETE']

    # All registered users must be able to post
    # Only way to allow moderators to create addresses
    __registered_methods__ = ['POST']

    email = Column(Unicode(100), unique=True, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupMember(Base):
    """Group member model."""

    __description__ = {
        'general': "Assignment of registered users to groups."
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['user_id', 'group.moderator_id']
    __owner_methods__ = ['GET', 'DELETE']

    __registered_methods__ = ['POST']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupForward(Base):
    """group forward model."""

    __description__ = {
        'general': "All messages to the group will be additionally forwarded"
        "to this address The group will NOT receive messages sent to this "
        "address, see /groupaddress for this.",
        'fields': {
            'email': "E-Mail address to which mails will be forwarded"
        }
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['group.moderator_id']
    __owner_methods__ = ['GET', 'DELETE']

    __registered_methods__ = ['POST']

    email = Column(Unicode(100), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


def make_groupdomain():
    """Create domain.

    This is a function so it can be called after models in all modules have
    been defined.
    """
    groupdomain = {}
    groupdomain.update(make_domain(Group))
    groupdomain.update(make_domain(GroupAddress))
    groupdomain.update(make_domain(GroupMember))
    groupdomain.update(make_domain(GroupForward))

    groupdomain['groups']['schema']['permissions'].update({
        'type': 'permissions_jsonschema'
    })

    groupdomain['groupaddresses']['schema']['group_id'].update({
        'only_groups_you_moderate': True,
        'unique_combination': ['email'],
        'not_patchable': True,
    })
    groupdomain['groupaddresses']['schema']['email'].update({
        'regex': EMAIL_REGEX,
        'unique_combination': ['group_id']})

    groupdomain['groupforwards']['schema']['group_id'].update({
        'only_groups_you_moderate': True,
        'unique_combination': ['email'],
        'not_patchable': True,
    })
    groupdomain['groupforwards']['schema']['email'].update({
        'regex': EMAIL_REGEX,
        'unique_combination': ['group_id']})

    groupdomain['groupmembers']['schema']['user_id'].update({
        'only_self_enrollment_for_group': True,
        'unique_combination': ['group_id']})
    groupdomain['groupmembers']['schema']['group_id'].update({
        'self_enrollment_must_be_allowed': True,
        'unique_combination': ['user_id']})

    # Membership is not transferable -> remove PUT and PATCH
    groupdomain['groupmembers']['item_methods'] = ['GET', 'DELETE']

    return groupdomain


class GroupValidator(object):
    """Custom Validator for group validation rules."""

    def _validate_only_self_enrollment_for_group(self, enabled, field, value):
        """Validate if the id can be used to enroll for a group.

        Users can only sign up themselves
        Moderators and admins can sign up everyone

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group_id = self.document.get('group_id', None)
            group = app.data.find_one("groups", None, id=group_id)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                moderator_id = group["moderator_id"]

                if not(g.resource_admin or (g.logged_in_user == value) or
                       (g.logged_in_user == moderator_id)):
                    self._error(field, "You can only enroll yourself. (%s: "
                                "%s is yours)." % (field, g.logged_in_user))

    def _validate_self_enrollment_must_be_allowed(self, enabled, field, value):
        """Validation for a group_id field in useraddressmembers.

        Validates if the group allows self enrollment.

        Except group moderator and admins, they can ignore this

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group = app.data.find_one("groups", None, id=value)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                moderator_id = group["moderator_id"]
                if not(g.resource_admin or
                       (g.logged_in_user == moderator_id) or
                       group["allow_self_enrollment"]):
                    # This copies the validation error for the case this group
                    # doesnt exist (since its hidden to the user)
                    self._error(field,
                                "value '%s' must exist in resource 'groups', "
                                "field 'id'." % value)

    def _validate_only_groups_you_moderate(self, enabled, field, value):
        """Validation for a group_id field in forwardaddresses.

        If you are not member or admin of the group you get the same
        error as if the group wouldn't exist

        If you are member, but not moderator, you will get a message that you
        cannot enter this group_id

        If you are moderator or have admin permissions it is alright.

        :param enabled: boolean, validates nothing if set to false
        :param field: field name.
        :param value: field value.
        """
        if enabled:
            # Get moderator id
            group = app.data.find_one("groups", None, id=value)

            # If the group doesnt exist we dont have to do anything,
            # The 'type' validator will generate an error anyway
            if group is not None:
                if not g.resource_admin:
                    moderator_id = group["moderator_id"]
                    if not(g.logged_in_user == moderator_id):
                        owners = get_owner(get_class_for_resource("groups"),
                                           value)
                        if g.logged_in_user in owners:
                            self._error(field, "you are not the moderator of"
                                        "this group.")
                        else:
                            # Not Member either
                            # Copies the validation error for the case this
                            # group doesnt exist (since its hidden to the user)
                            self._error(field,
                                        "value '%s' must exist in resource "
                                        "'groups', field 'id'." % value)

    def _validate_type_permissions_jsonschema(self, field, value):
        """Validate jsonschema provided using the python jsonschema library.

        :param jsonschema: The jsonschema to use
        :param field: field name.
        :param value: field value.
        """
        schema = create_group_permissions_jsonschema()

        try:
            jsonschema.validate(value, schema)
        except jsonschema.exceptions.ValidationError as v_error:
            # Something was not according to schema
            self._error(field, v_error.message)


def create_group_permissions_jsonschema():
    """Create a jsonschema of valid group permissions.

    Returns:
        (dict) the jsonschema
    """
    # Create outer container
    # Properties will be the enpoints
    # additionalProperties has to be false, otherwise all unknown properties
    # are accepted
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Permission Matrix Schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {}
    }

    # Now add endpoints as allowed properties
    # This is the inner container, they are again objects
    for res in app.config['DOMAIN']:
        schema["properties"][res] = {
            "title": "Permissions for '%s' resource" % res,
            "type": "object",
            "additionalProperties": False,
            "properties": {}
        }

        subschema = schema["properties"][res]["properties"]

        # All basic methods covered, just boolean
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            subschema[method] = {
                "title": 'Permission for %s' % method,
                "type": "boolean"
            }

    return schema


def check_group_permission(user_id, resource, method):
    """Check group permissions of user.

    This function checks wether the user is permitted to access
    the given resource with the given method based on the groups
    he is in.

    :param user_id: the id of the user to check
    :param resource: the requested resource
    :param method: the used method

    :returns: Boolean, True if permitted, False otherwise
    """
    db = app.data.driver.session
    query = db.query(Group.permissions).filter(
        Group.members.any(GroupMember.user_id == user_id))

    # All entries are dictionaries
    # If any dicitionary contains the permission it is good.
    for row in query:
        if (row.permissions and
                (row.permissions.get(resource, {}).get(method, False))):
            return True

    return False


def _get_filename(email):
    """Generate the filename for a mailinglist for itet mail forwarding.

    :param email: adress of the mailinglist
    :returns: path of forward file
    """
    return config.FORWARD_DIR + '/.forward+' + email


def _add_email(group_id, email):
    """Add an address to the mailinglist file.

    :param group_id: id of Group object(which addresses are forwarded)
    :param email: address to forward to to add(where to forward)
    """
    db = app.data.driver.session

    groupaddresses = db.query(GroupAddress).filter(
        GroupAddress.group_id == group_id)
    for groupaddress in groupaddresses:
        try:
            with open(_get_filename(groupaddress.email), 'a') as f:
                f.write(email + '\n')
        except IOError as e:
            app.logger.error(str(e) + "Can not open forward file! "
                             "Please check permissions!")
            abort(500)


def _remove_email(group_id, email):
    """Remove an address from a mailinglist file.

    :param group_id: id of Group object
    :param email: Address to forward to to remove
    """
    db = app.data.driver.session

    groupaddresses = db.query(GroupAddress).filter(
        GroupAddress.group_id == group_id)
    for groupaddress in groupaddresses:
        path = _get_filename(groupaddress.email)
        try:
            with open(path, 'r') as f:
                lines = [x for x in f.readlines() if x != email + '\n']
            with open(path, 'w') as f:
                f.write(''.join(lines))
        except IOError as e:
            app.logger.error(str(e) + "Can not remove forward " + email +
                             " from " + path + "! It seems the forward"
                             " database is inconsistent!")


def add_user(group_id, user_id):
    """Add a user to all GroupAddresses of a group in the filesystem.

    :param group_id: id of the group object
    :param user_id: id of the user to add
    """
    db = app.data.driver.session
    user = db.query(User).get(user_id)

    _add_email(group_id, user.email)


def remove_user(group_id, user_id):
    """Remove a user from a group in the filesystem.

    :param group_id: id of the group object
    :param user_id: id of the user to remove
    """
    db = app.data.driver.session
    user = db.query(User).get(user_id)

    _remove_email(group_id, user.email)


# Hooks for groupaddresses, all methods needed


def create_files(items):
    """Create mailinglist files.

    Hook to add all users in group to a file for the address, necessary
    when the address is added to an existing group to get it up to date
    """
    session = app.data.driver.session

    for item in items:
        # Get members in group
        members = session.query(GroupMember).filter_by(
            group_id=item['group_id']).all()
        members = [groupmember.user.email for groupmember in members]

        forwards = session.query(GroupForward).filter_by(
            group_id=item['group_id']).all()
        forwards = [f.email for f in forwards]

        for email in members + forwards:
            _add_email(item['group_id'], email)


def delete_file(item):
    """Hook to delete a the mailinglist file when the address is removed.

    :param item: address which is being deleted
    """
    path = _get_filename(item['email'])

    try:
        remove(path)
    except OSError as e:
        app.logger.error(str(e) + "Can not remove forward " +
                         item['email'] + "! It seems the forward "
                         "database is inconsistent!")
        pass


def update_file(updates, original):
    """Rename the file to the new address."""
    if 'email' in updates:
        old_path = _get_filename(original['email'])
        new_path = _get_filename(updates['email'])

        try:
            rename(old_path, new_path)
        except OSError as e:
            app.logger.error(str(e) + "Can not rename file " +
                             original['email'] + "to " + updates['email'] +
                             "! It seems the forward database is " +
                             "inconsistent!")


# Hooks for groupmembers, only POST and DELETE needed

def add_user_email(items):
    """Add user to list.

    Hook to add a user to a forward in the filesystem when a ForwardUser
    object is created

    :param items: GroupMember objects
    """
    for i in items:
        add_user(i['group_id'], i['user_id'])


def remove_user_email(item):
    """Remove user from list.

    Hook to remove the entries in the forward files in the filesystem when
    a GroupMember is DELETEd

    :param item: dict of the GroupMember which is deleted
    """
    remove_user(item['group_id'], item['user_id'])


# Hooks for groupforwards, all methods needed


def add_forward_email(items):
    """Add mail to list.

    Hook to add an entry to a forward file in the filesystem when a
    GroupAddressMember object is created using POST

    :param items: List of new GroupAddressMember objects
    """
    for forward in items:
        _add_email(forward['group_id'], forward['email'])


def replace_forward_email(item, original):
    """Replace mail in list.

    Hook to replace an entry in forward files in the filesystem when a
    GroupAddressMember object is replaced using PUT

    :param item: New GroupAddressMember object to be registered
    :param original: The old GroupAddressMember object
    """
    _remove_email(original['group_id'], original['email'])
    _add_email(item['group_id'], item['email'])


def update_forward_email(updates, original):
    """Update mail in list.

    Hook to update an entry in forward files in the filesystem when a
    GroupAddressMember object is changed using PATCH

    :param updates: dict of updates to GroupAddressMember object
    :param original: The old GroupAddressMember object
    """
    new_item = original.copy()
    new_item.update(updates)
    replace_forward_email(new_item, original)


def remove_forward_email(item):
    """Delete mail from list.

    Hook to remove an entry in forward files in the filesystem when a
    GroupAddressMember object is DELETEd

    :param item: The GroupAddressMember object which is being deleted
    """
    _remove_email(item['group_id'], item['email'])


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_groupdomain())
    register_validator(app, GroupValidator)

    # email-management
    # Addresses
    app.on_inserted_groupaddresses += create_files
    app.on_replaced_groupaddresses += update_file
    app.on_updated_groupaddresses += update_file
    app.on_deleted_item_groupaddresses += delete_file
    # Members - can not be updated or replaced
    app.on_inserted_groupmembers += add_user_email
    app.on_deleted_item_groupmembers += remove_user_email
    # Forwards
    app.on_inserted_groupforwards += add_forward_email
    app.on_replaced_groupforwards += replace_forward_email
    app.on_updated_groupforwards += update_forward_email
    app.on_deleted_item_groupforwards += remove_forward_email
