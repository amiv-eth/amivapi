# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

import os

from flask import current_app as app
from flask import abort

from eve.utils import config

from amivapi.models import User, GroupAddress


def get_file_for_groupaddress(groupaddress_id):
    """ Generates the filename for a forward file for itet mail forwarding

    :param groupaddress_id: The id of the groupaddress object(which
                              address is forwarded)
    :returns: path of forward file
    """
    db = app.data.driver.session
    groupaddress = db.query(GroupAddress).get(groupaddress_id)
    return config.FORWARD_DIR + '/.forward+' + groupaddress.email


def add_address_to_lists(group_id, address):
    """ Adds an address to the forward files of a group on the server

    :param group_id: id of Group object(which addresses are forwarded)
    :param address: address to forward to to add(where to forward)
    """
    db = app.data.driver.session

    groupaddresses = db.query(GroupAddress).filter(
        GroupAddress.group_id == group_id)
    for groupaddress in groupaddresses:
        try:
            with open(get_file_for_groupaddress(groupaddress.id), 'a') as f:
                f.write(address + '\n')
        except IOError as e:
            app.logger.error(str(e) + "Can not open forward file! "
                             + "Please check permissions!")
            abort(500)


def remove_address_from_lists(group_id, address):
    """ Removes an address from a forward files of a group on the server

    :param group_id: id of Group object
    :param address: Address to forward to to remove
    """
    db = app.data.driver.session

    groupaddresses = db.query(GroupAddress).filter(
        GroupAddress.group_id == group_id)
    for groupaddress in groupaddresses:
        path = get_file_for_groupaddress(groupaddress.id)
        try:
            with open(path, 'r') as f:
                lines = [x for x in f.readlines() if x != address + '\n']
            with open(path, 'w') as f:
                f.write(''.join(lines))
        except IOError as e:
            app.logger.error(str(e) + "Can not remove forward " + address
                             + " from " + path + "! It seems the forward"
                             + " database is inconsistent!")
            pass


def remove_list(groupaddress):
    """ Removes a forward file from the server

    :param groupaddress: groupaddress object associated with the file
    """
    path = config.FORWARD_DIR + '/.forward+' + groupaddress['email']
    try:
        os.remove(path)
    except OSError as e:
        app.logger.error(str(e) + "Can not remove forward "
                         + groupaddress['email'] + "! It seems the forward "
                         "database is inconsistent!")
        pass


def add_user(group_id, user_id):
    """ Add a user to all GroupAddresses of a group in the filesystem

    :param group_id: id of the group object
    :param user_id: id of the user to add
    """
    db = app.data.driver.session
    user = db.query(User).get(user_id)

    add_address_to_lists(group_id, user.email)


def remove_user(group_id, user_id):
    """ Remove a user from a group in the filesystem

    :param group_id: id of the group object
    :param user_id: id of the user to remove
    """
    db = app.data.driver.session
    user = db.query(User).get(user_id)

    remove_address_from_lists(group_id, user.email)


#
#
# Hooks for changes to forwards
#
#


def on_groupaddress_deleted(item):
    """ Hook to delete a list in the filesystem when the object is deleted

    :param item: forward object which is being deleted
    """
    remove_list(item)


#
#
# Hooks for changes to GroupMembers
#
#


def on_groupmember_inserted(items):
    """ Hook to add a user to a forward in the filesystem when a ForwardUser
    object is created

    :param items: GroupMember objects
    """
    for i in items:
        add_user(i['group_id'], i['user_id'])


def on_groupmember_replaced(item, original):
    """ Hook to replace a user in a group in the forward filesystem when a
    GroupMember object is replaced using PUT

    :param item: new GroupMember object
    :param original: old GroupMember object, which is being deleted
    """
    remove_user(original['group_id'], original['user_id'])
    add_user(item['group_id'], item['user_id'])


def on_groupmember_updated(updates, original):
    """ Hook to update an entry in a forward file in the filesystem when a
    GroupMember object is PATCHed

    :param updates: dict containing changes to GroupMember
    :param original: dict of original object
    """
    new_item = original.copy()
    new_item.update(updates)
    on_groupmember_replaced(new_item, original)


def on_groupmember_deleted(item):
    """ Hook to remove the entries in the forward files in the filesystem when
    a GroupMember is DELETEd

    :param item: dict of the GroupMember which is deleted
    """
    remove_user(item['group_id'], item['user_id'])


#
#
# Hooks for changes to groupaddresses
#
#


def on_groupaddressmember_inserted(items):
    """ Hook to add an entry to a forward file in the filesystem when a
    GroupAddressMember object is created using POST

    :param items: List of new GroupAddressMember objects
    """
    for i in items:
        add_address_to_lists(i['group_id'], i['email'])


def on_groupaddressmember_replaced(item, original):
    """ Hook to replace an entry in forward files in the filesystem when a
    GroupAddressMember object is replaced using PUT

    :param item: New GroupAddressMember object to be registered
    :param original: The old GroupAddressMember object
    """
    remove_address_from_lists(original['group_id'], original['email'])
    add_address_to_lists(item['group_id'], item['email'])


def on_groupaddressmember_updated(updates, original):
    """ Hook to update an entry in forward files in the filesystem when a
    GroupAddressMember object is changed using PATCH

    :param updates: dict of updates to GroupAddressMember object
    :param original: The old GroupAddressMember object
    """
    new_item = original.copy()
    new_item.update(updates)
    on_groupaddressmember_replaced(new_item, original)


def on_groupaddressmember_deleted(item):
    """ Hook to remove an entry in forward files in the filesystem when a
    GroupAddressMember object is DELETEd

    :param item: The GroupAddressMember object which is being deleted
    """
    remove_address_from_lists(item['group_id'], item['email'])
