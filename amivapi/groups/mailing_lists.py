# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Api group resources.

Contains groups, groupmemberships, groupaddresses and forwards as well as
group permission and mailinglist functions.
"""

from os import remove, rename

from flask import current_app as app
from flask import abort

from eve.utils import config

from amivapi.models import User

from .settings import GroupMember, GroupAddress, GroupForward


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
