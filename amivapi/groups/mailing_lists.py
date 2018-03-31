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

 The files can be created locally or remotely via ssh, to support the current
 mailing list server solution in place.

 Ssh is probably not the best approach for this, but unfortunately the server
 does not support any other type of connection.
 If this changes, this implementation should be updated.
"""

from itertools import chain
from os import makedirs, path, remove
from subprocess import Popen, PIPE
from typing import Iterable, Optional

from bson import ObjectId

from flask import current_app


# Hooks

def new_groups(groups: Iterable[dict]) -> None:
    """Create mailing list files for all new groups."""
    for group in groups:
        make_files(group['_id'])


def updated_group(updates: dict, original: dict) -> None:
    """Update group mailing lists if any address changes."""
    # Remove no longer needed forwards
    if 'receive_from' in updates:
        remove_files(address for address in original.get('receive_from', [])
                     if address not in updates['receive_from'])
    # Update remaining forwards
    if ('receive_from' in updates) or ('forward_to' in updates):
        make_files(original['_id'])


def removed_group(group: dict) -> None:
    """Delete all mailinglist files."""
    remove_files(group.get('receive_from', []))


def new_members(new_memberships: Iterable[dict]) -> None:
    """Post on memberships, recreate files for the groups"""
    # Get group ids without duplicates
    group_ids = set(m['group'] for m in new_memberships)

    for group_id in group_ids:
        make_files(group_id)


def removed_member(member: dict) -> None:
    """Update files for the group the user was in."""
    make_files(member['group'])


def updated_user(updates: dict, original: dict) -> None:
    """Update group mailing files if a member changes his email."""
    if 'email' in updates:
        memberships = current_app.data.driver.db['groupmemberships'].find(
            {'user': ObjectId(original['_id'])}, {'group': 1})

        for membership in memberships:
            make_files(str(membership['group']))


# File Handling

def make_files(group_id: str) -> None:
    """Create all mailing lists for a group.

    If the file exists it will be overwritten.
    If `MAILING_LIST_DIR` set in config, create a local file.
    If `REMOTE_MAILING_LIST_ADDRESS` set in config, create remote file.

    Args:
        group_id: The id of the group
    """
    # Check if any file will be created, otherwise avoid db access
    if (current_app.config['MAILING_LIST_DIR'] or
            current_app.config['REMOTE_MAILING_LIST_ADDRESS']):
        group_objectid = ObjectId(group_id)

        # Get group, ensure to include mail addresses
        group = current_app.data.driver.db['groups'].find_one(
            {'_id': group_objectid}, {'receive_from': 1, 'forward_to': 1})

        if group:
            # get mail addresses of all users in group
            memberships = current_app.data.driver.db['groupmemberships'].find(
                {'group': group_objectid}, {'user': 1})
            user_ids = [membership['user'] for membership in memberships]
            users = current_app.data.driver.db['users'].find(
                {'_id': {'$in': user_ids}}, {'email': 1})
            user_mails = (user['email'] for user in users)

            # file content: user mails and 'forward_to' entries
            # The empty string (last arg) ensures that the data ends with '\n'
            content = '\n'.join(chain(group.get('forward_to', []),
                                      user_mails,
                                      ''))

            # A file is required for each 'receive_from' entry
            for address in group.get('receive_from', []):
                # Local
                local_dir = current_app.config['MAILING_LIST_DIR']
                if local_dir:
                    # Create directory if needed
                    if not path.isdir(local_dir):
                        makedirs(local_dir)

                    with open(_get_local_path(address), 'w') as file:
                        file.write(content)
                        file.truncate()  # If old file was larger, cut of rest

                # Remote
                if current_app.config['REMOTE_MAILING_LIST_ADDRESS']:
                    ssh_create(address, content)


def remove_files(addresses: Iterable[str]) -> None:
    """Remove several mailing list files.

    If `MAILING_LIST_DIR` set in config, create a local file.
    If `REMOTE_MAILING_LIST_ADDRESS` set in config, create remote file.

    Args:
        addresses: email addresses with a forward file to delete
    """
    for address in addresses:
        # Local
        if current_app.config['MAILING_LIST_DIR']:
            try:
                remove(_get_local_path(address))
            except OSError as error:
                current_app.logger.error(
                    str(error) + "\nCan not remove mailing list '%s' ! The "
                    "mailing list database seems to be inconsistent!"
                    % address)

        # Remote
        if current_app.config['REMOTE_MAILING_LIST_ADDRESS']:
            ssh_remove(address)


def _get_local_path(email: str) -> str:
    """Local path for a mailinglist for itet mail forwarding."""
    return path.join(current_app.config['MAILING_LIST_DIR'],
                     current_app.config['MAILING_LIST_FILE_PREFIX'] + email)


def _get_remote_path(email: str) -> str:
    """Remote path for a mailinglist for itet mail forwarding."""
    return path.join(current_app.config['REMOTE_MAILING_LIST_DIR'],
                     current_app.config['MAILING_LIST_FILE_PREFIX'] + email)


# SSH Helpers (in separate functions for easier testing)

def ssh_create(address: str, content: str) -> None:
    """Create a file with content remotely over ssh."""
    # Create dir, then use 'cat - ' to listen to stdin
    # Create temporary file first, if upload is completed replace
    folder = current_app.config['REMOTE_MAILING_LIST_DIR']
    file = _get_remote_path(address)
    tempfile = file + '.tmp'
    ssh_command('mkdir -p %s; cat - > %s; mv %s %s;'
                % (folder, tempfile, tempfile, file), input=content)


def ssh_remove(address: str) -> None:
    """Remove a file remotely over ssh."""
    path = _get_remote_path(address)
    try:
        ssh_command('rm %s' % path)
    except RuntimeError as e:
        # File does not exist: log issue, but do not raise exception
        no_file_error = ("rm: cannot remove '%s': No such file or directory" %
                         path)
        if no_file_error in str(e):
            current_app.logger.error(
                "Cannot remove remote mailing list '%s' because the file does "
                "not exist. The mailing list database seems to be"
                "inconsistent." % address)
        else:
            raise e


def ssh_command(remote_command: str, input: str = None) -> Optional[str]:
    """Call the given command remotely via ssh with input (if given).

    Popen and communicate are used for compatibility with both python 2 and 3.

    Args:
        remote_command: Command to execute on remote server
        input: Input, is sent to remote process via stdin

    Returns:
        stdout of command

    Raises:
        RuntimeError: An error with the ssh connection occured.
    """
    keyfile = current_app.config.get('REMOTE_MAILING_LIST_KEYFILE')  # optional
    address = current_app.config['REMOTE_MAILING_LIST_ADDRESS']

    # Construct local ssh command, use -i option if keyfile is specified
    cmd = (["ssh"] + (['-i', keyfile] if keyfile else []) +
           [address, remote_command])

    # Open subprocess, initialize pipes for input and errors
    process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    # Send input (as bytes) and receive errors (will also be bytes)
    out, error = process.communicate(input=input.encode() if input else None)

    # Raise RuntimeError if anything went wrong
    if error:
        raise RuntimeError("Executing command via ssh failed with error:\n%s"
                           % error.decode())

    if out:
        return out.decode()

    return None
