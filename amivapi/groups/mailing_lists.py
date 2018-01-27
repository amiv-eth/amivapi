# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Api group emails.

A email list can be generated for any group.
Everytime a group changes or a groupmember is added/removed, the group mail
files will be regenerated.
(Since we do not get thousands of requests like this per second we don't need
 anything fancy.)
"""

from itertools import chain
from os import makedirs, path, remove

from bson import ObjectId

from flask import current_app


def make_files(group_id):
    """Create all mailing lists for a group.

    If the file exists it will be overwritten.

    If `MAILING_LIST_DIR` is not set in the config (or empty), nothing happens.

    Args:
        group_id (str): The id of the group
    """
    if not current_app.config.get('MAILING_LIST_DIR'):
        return

    group_objectid = ObjectId(group_id)

    # Get group
    group = current_app.data.driver.db['groups'].find_one(
        {'_id': group_objectid}, {'receive_from': 1, 'forward_to': 1})

    if group:
        # Get user mails
        memberships = current_app.data.driver.db['groupmemberships'].find(
            {'group': group_objectid}, {'user': 1})
        user_ids = [membership['user'] for membership in memberships]
        users = current_app.data.driver.db['users'].find(
            {'_id': {'$in': user_ids}}, {'email': 1})
        user_mails = (user['email'] for user in users)

        # The empty string at the chain end ensures we end the data with \n
        addresses = '\n'.join(chain(group.get('forward_to', []),
                                    user_mails,
                                    ''))

        # Create all needed forwards
        for listname in group.get('receive_from', []):
            # Check if directory needs to be created
            forward_path = current_app.config['MAILING_LIST_DIR']
            if not path.isdir(forward_path):
                makedirs(forward_path)

            with open(_get_filename(listname), 'w') as file:
                file.write(addresses)
                file.truncate()  # Needed if old file was bigger


def remove_files(addresses):
    """Create several mailing list files

    If `MAILING_LIST_DIR` is not set in the config (or empty), nothing happens.

    Args:
        addresses (list): email addresses with a forward file to delete
    """
    if not current_app.config.get('MAILING_LIST_DIR'):
        return

    for address in addresses:
        try:
            remove(_get_filename(address))
        except OSError as error:
            current_app.logger.error(
                str(error) + "\nCan not remove forward %s ! It seems the "
                "forward database is inconsistent!" % address)


def _get_filename(email):
    """Generate the filename for a mailinglist for itet mail forwarding."""
    return path.join(current_app.config['MAILING_LIST_DIR'],
                     current_app.config['MAILING_LIST_FILE_PREFIX'] + email)


# Hooks

def new_groups(groups):
    """Create mailing list files for all new groups."""
    for group in groups:
        make_files(group['_id'])


def updated_group(updates, original):
    """Update group mailing lists if any address changes."""
    # This is just the simplest solution. Could be advanced if needed.
    if ('receive_from' in updates) or ('forward_to' in updates):
        remove_files(original.get('receive_from', []))
        make_files(original['_id'])


def removed_group(group):
    """Delete all mailinglist files."""
    print(group)
    remove_files(group.get('receive_from', []))


def new_members(new_memberships):
    """Post on memberships, recreate files for the groups"""
    # Get group ids without duplicates
    group_ids = set(m['group'] for m in new_memberships)

    for group_id in group_ids:
        make_files(group_id)


def removed_member(member):
    """Update files for the group the user was in."""
    make_files(member['group'])


def updated_user(updates, original):
    """Update group mailing files if a member changes his email."""
    if 'email' in updates:
        memberships = current_app.data.driver.db['groupmemberships'].find(
            {'user': ObjectId(original['_id'])}, {'group': 1})

        for membership in memberships:
            make_files(str(membership['group']))
