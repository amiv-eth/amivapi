import os

from flask import current_app as app
from flask import abort

from eve.utils import config

from amivapi.models import User, Forward


def get_file_for_forward(forward_id):
    db = app.data.driver.session
    forward = db.query(Forward).get(forward_id)
    return config.FORWARD_DIR + '/.forward+' + forward.address


def add_address_to_list(forward_id, address):
    try:
        with open(get_file_for_forward(forward_id), 'a') as f:
            f.write(address + '\n')
    except IOError, e:
        app.logger.error(str(e) + "Can not open forward file! "
                         + "Please check permissions!")
        abort(500)


def remove_address_from_list(forward_id, address):
    path = get_file_for_forward(forward_id)
    try:
        with open(path, 'r') as f:
            lines = [x for x in f.readlines() if x != address + '\n']
        with open(path, 'w') as f:
            f.write(''.join(lines))
    except IOError, e:
        app.logger.error(str(e) + "Can not remove forward " + address
                         + " from " + path + "! It seems the forward database"
                         + " is inconsistent!")
        pass


def remove_list(forward):
    path = config.FORWARD_DIR + '/.forward+' + forward['address']
    try:
        os.remove(path)
    except OSError, e:
        app.logger.error(str(e) + "Can not remove forward "
                         + forward['address'] + "! It seems the forward "
                         "database is inconsistent!")
        pass


def add_user(forward_id, user_id):
    db = app.data.driver.session
    user = db.query(User).get(user_id)
    add_address_to_list(forward_id, user.email)


def remove_user(forward_id, user_id):
    db = app.data.driver.session
    user = db.query(User).get(user_id)
    remove_address_from_list(forward_id, user.email)


""" Hooks for changes to forwards """


def on_forward_deleted(item):
    remove_list(item)


""" Hooks for changes to forwardusers """


def on_forwarduser_inserted(items):
    for i in items:
        add_user(i['forward_id'], i['user_id'])


def on_forwarduser_replaced(item, original):
    remove_user(original['forward_id'], original['user_id'])
    add_user(item['forward_id'], item['user_id'])


def on_forwarduser_updated(updates, original):
    new_item = original.copy()
    new_item.update(updates)
    on_forwarduser_replaced(new_item, original)


def on_forwarduser_deleted(item):
    remove_user(item['forward_id'], item['user_id'])


""" Hooks for changes to forwardaddresses """


def on_forwardaddress_inserted(items):
    for i in items:
        add_address_to_list(i['forward_id'], i['address'])


def on_forwardaddress_replaced(item, original):
    remove_address_from_list(original['forward_id'], original['address'])
    add_address_to_list(item['forward_id'], item['address'])


def on_forwardaddress_updated(updates, original):
    new_item = original.copy()
    new_item.update(updates)
    on_forwardaddress_replaced(new_item, original)


def on_forwardaddress_deleted(item):
    remove_address_from_list(item['forward_id'], item['address'])
