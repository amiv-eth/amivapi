# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Ldap connection using the nethz module.

Can be used to authenticate and update users.
Don't forget to call `init_app' to set up the connection.
The app configuration needs to contain the following ldap entries:
- `LDAP_USER'
- `LDAP_PASS'

Possible improvements:
- The `_process_data' function is rather complicated. Maybe some parts could
  be improved or moved to the nethz module?
- `_create_or_patch_user' is also not very straightforward, maybe the ldap
  importing logic could be simplified?


Note on department info in ldap:

We can discover a user's department by looking at the `departmentNumber` field.
Contrary to its name, it does not contain a number, but entries like this:

- `ETH Studentin D-ITET, Elektrotechnik und Interformationstechnologie Bsc.`
- `ETH Student D-MAVT, Doktorand`

and similar. For regular, mobility and phd students the starting part is
always the same, and the second part of the string contains further details.

We therefore match the first part of the `departmentNumber` field to
check for the department. In the app settings, we define which substring
is mapped to which department.
"""

from eve.methods.patch import patch_internal
from eve.methods.post import post_internal
from flask import current_app
from nethz.ldap import AuthenticatedLdap

from amivapi.utils import admin_permissions


def init_app(app):
    """Attach an ldap connection to the app."""
    user = app.config['LDAP_USERNAME']
    password = app.config['LDAP_PASSWORD']

    if user is None and password is None:
        return

    if None in (user, password):
        raise ValueError("You cannot set only a username or only a password "
                         "for ldap.")

    app.config['ldap_connector'] = AuthenticatedLdap(user, password)


def authenticate_user(cn, password):
    """Try to authenticate a user with ldap.

    Args:
        cn (string): the common name to search ldap for -> the nethz name
        password (string): the user password (plaintext)

    Returns:
        bool: True if successful, False otherwise
    """
    return current_app.config['ldap_connector'].authenticate(cn, password)


def sync_one(cn):
    """Synchronize ldap and database for a single user.

    The cn will be escaped for ldap, no need to worry about this.

    Args:
        cn (string): Common name of user.

    Returns:
        dict: Data of updated or newly created user in database,
              None if user not found in ldap.
    """
    query = "(cn=%s)" % _escape(cn)
    ldap_data = next(_search(query), None)

    if ldap_data:
        return _create_or_update_user(ldap_data)


def sync_all():
    """Query the ETH LDAP for all our members. Adds non-existing ones to db.

    Updates existing ones if ldap data has changed.
    Depending on the system, this can take 30 seconds or longer.

    Returns:
        list: Data of all updated users.
    """
    # See file docstring for explanation of `deparmentNumber` field
    keywords = ''.join(u"(departmentNumber=*%s*)" % _escape(item)
                       for item in current_app.config['LDAP_DEPARTMENT_MAP'])
    query = u"(& (ou=VSETH Mitglied) (| %s) )" % keywords
    ldap_data = _search(query)

    return [_create_or_update_user(user) for user in ldap_data]


def _search(query):
    """Search the LDAP. Returns filtered data (iterable) for string query."""
    attr = [
        'cn',
        'swissEduPersonMatriculationNumber',
        'givenName',
        'sn',
        'swissEduPersonGender',
        'departmentNumber',
        'ou'
    ]
    results = current_app.config['ldap_connector'].search(query,
                                                          attributes=attr)
    return (_process_data(res) for res in results)


def _escape(query):
    """LDAP-style escape according to the ldap3 documentation."""
    replacements = (
        ('\\', r'\5C'),  # Do this first or we'll break the other replacements
        ('*', r'\2A'),
        ('(', r'\28'),
        (')', r'\29'),
        (chr(0), r'\00')
    )
    for old, new in replacements:
        query = query.replace(old, new)

    return query


def _process_data(data):
    """Utility to filter ldap data.

    It will take all fields relevant for a user update and map them
    to the correct fields for the user resource.
    """
    res = {'nethz': data['cn'][0],
           'legi': data['swissEduPersonMatriculationNumber'],
           'firstname': data['givenName'][0],
           'lastname': data['sn'][0]}
    # email can be removed when Eve switches to Cerberus 1.x, then
    # We could do this as a default value in the user model
    res['email'] = '%s@ethz.ch' % res['nethz']
    res['gender'] = \
        u"male" if int(data['swissEduPersonGender']) == 1 else u"female"

    # See file docstring for explanation of `deparmentNumber` field
    # In some rare cases, the departmentNumber field is either empty
    # or missing -> normalize to empty string
    department_number = next(iter(data.get('departmentNumber', [])), '')
    department_map = current_app.config['LDAP_DEPARTMENT_MAP'].items()
    department = (dept for phrase, dept in department_map
                  if phrase in department_number)
    res['department'] = next(department, None)  # None if no match

    # Membership: One of our departments and VSETH member
    is_member = ((res['department'] is not None) and
                 ('VSETH Mitglied' in data['ou']))
    res['membership'] = u"regular" if is_member else u"none"

    return res


def _create_or_update_user(ldap_data):
    """Try to find user in database. Update if it exists, create otherwise."""
    query = {'nethz': ldap_data['nethz']}
    db_data = current_app.data.driver.db['users'].find_one(query)

    with admin_permissions():
        if db_data:
            # Membership will not be downgraded and email not be overwritten
            ldap_data.pop('email', None)
            if db_data.get('membership') != u"none":
                ldap_data.pop('membership', None)

            user = patch_internal('users',
                                  ldap_data,
                                  _id=db_data['_id'])[0]
        else:
            user = post_internal('users', ldap_data)[0]

    return user
