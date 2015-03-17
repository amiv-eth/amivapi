# -*- coding: utf-8 -*-
#
# AMIVAPI forwards.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

from flask import current_app as app
from flask import abort

from eve.utils import config

from amivapi.models import User, Forward


def get_file_for_forward(forward_id):
    """ Generates the filename for a forward file for itet mail forwarding

    :param forward_id: The id of the forward object
    :returns: path of forward file
    """
    db = app.data.driver.session
    forward = db.query(Forward).get(forward_id)
    return config.FORWARD_DIR + '/.forward+' + forward.address


def add_address_to_list(forward_id, address):
    """ Adds an address to a forward file on the server

    :param forward_id: id of forward object
    :param address: address to forward to to add
    """
    try:
        with open(get_file_for_forward(forward_id), 'a') as f:
            f.write(address + '\n')
    except IOError as e:
        app.logger.error(str(e) + "Can not open forward file! "
                         + "Please check permissions!")
        abort(500)


def remove_address_from_list(forward_id, address):
    """ Removes an address from a forward file on the server

    :param forward_id: id of forward object
    :param address: Address to forward to to remove
    """
    path = get_file_for_forward(forward_id)
    try:
        with open(path, 'r') as f:
            lines = [x for x in f.readlines() if x != address + '\n']
        with open(path, 'w') as f:
            f.write(''.join(lines))
    except IOError as e:
        app.logger.error(str(e) + "Can not remove forward " + address
                         + " from " + path + "! It seems the forward database"
                         + " is inconsistent!")
        pass


def remove_list(forward):
    """ Removes a forward file from the server

    :param forward: forward object associated with the file
    """
    path = config.FORWARD_DIR + '/.forward+' + forward['address']
    try:
        os.remove(path)
    except OSError as e:
        app.logger.error(str(e) + "Can not remove forward "
                         + forward['address'] + "! It seems the forward "
                         "database is inconsistent!")
        pass


def add_user(forward_id, user_id):
    """ Add a user to a forward list in the filesystem

    :param forward_id: id of the forward object
    :param user_id: id of the user to add
    """
    db = app.data.driver.session
    user = db.query(User).get(user_id)
    add_address_to_list(forward_id, user.email)


def remove_user(forward_id, user_id):
    """ Remove a user from a forward list in the filesystem

    :param forward_id: id of the forward object
    :param user_id: id of the user to remove
    """
    db = app.data.driver.session
    user = db.query(User).get(user_id)
    remove_address_from_list(forward_id, user.email)


#
#
# Hooks for changes to forwards
#
#


def on_forward_deleted(item):
    """ Hook to delete a list in the filesystem when the object is deleted

    :param item: forward object which is being deleted
    """
    remove_list(item)


#
#
# Hooks for changes to forwardusers
#
#


def on_forwarduser_inserted(items):
    """ Hook to add a user to a forward in the filesystem when a ForwardUser
    object is created

    :param items: ForwardUser objects
    """
    for i in items:
        add_user(i['forward_id'], i['user_id'])


def on_forwarduser_replaced(item, original):
    """ Hook to replace a user in a forward in the filesystem when a
    ForwardUser object is replaced using PUT

    :param item: new ForwardUser object
    :param original: old ForwardUser object, which is being deleted
    """
    remove_user(original['forward_id'], original['user_id'])
    add_user(item['forward_id'], item['user_id'])


def on_forwarduser_updated(updates, original):
    """ Hook to update an entry in a forward file in the filesystem when a
    ForwardUser object is PATCHed

    :param updates: dict containing changes to ForwardUser
    :param original: dict of original object
    """
    new_item = original.copy()
    new_item.update(updates)
    on_forwarduser_replaced(new_item, original)


def on_forwarduser_deleted(item):
    """ Hook to remove the entry in the forward file in the filesystem when
    a forwarduser is DELETEd

    :param item: dict of the ForwardUser which is deleted
    """
    remove_user(item['forward_id'], item['user_id'])


#
#
# Hooks for changes to forwardaddresses
#
#


def on_forwardaddress_inserted(items):
    """ Hook to add an entry to a forward file in the filesystem when a
    ForwardAddress object is created using POST

    :param items: List of new ForwardAddress objects
    """
    for i in items:
        add_address_to_list(i['forward_id'], i['address'])


def on_forwardaddress_replaced(item, original):
    """ Hook to replace an entry in a forward file in the filesystem when a
    ForwardAddress object is replaced using PUT

    :param item: New ForwardAddress object to be registered
    :param original: The old ForwardAddress object
    """
    remove_address_from_list(original['forward_id'], original['address'])
    add_address_to_list(item['forward_id'], item['address'])


def on_forwardaddress_updated(updates, original):
    """ Hook to update an entry in a forward file in the filesystem when a
    ForwardAddress object is changed using PATCH

    :param updates: dict of updates to ForwardAddress object
    :param original: The old ForwardAddress object
    """
    new_item = original.copy()
    new_item.update(updates)
    on_forwardaddress_replaced(new_item, original)


def on_forwardaddress_deleted(item):
    """ Hook to remove an entry in a forward file in the filesystem when a
    ForwardAddress object is DELETEd

    :param item: The ForwardAddress object which is being deleted
    """
    remove_address_from_list(item['forward_id'], item['address'])
