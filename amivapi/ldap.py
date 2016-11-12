# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Ldap connection for the api."""

import re

from flask import current_app
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from amivapi.models import User
from nethz import ldap


class LdapConnector():
    """LDAP Connector.

    With all functions required for the app object.
    Can authenticate a user and provide up-to-date information for ETH LDAP.

    The app config needs to contain the following keys:
        LDAP_USER
        LDAP_PASS
        LDAP_MEMBER_OU_LIST

    Args:
        app (optional[Flaskapp]): The app object, defaults to None.
            If you don't provide it when initializing, don't forget
            to call ``init_app``
    """

    def __init__(self, app=None):
        """Init the connector."""
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize me like one of your flask extensions."""
        user = app.config['LDAP_USER']
        password = app.config['LDAP_PASS']
        self.ldap = ldap.AuthenticatedLdap(user, password)

    # The LDAP attributes we need for the api
    LDAP_ATTR = [
        'cn',
        'swissEduPersonMatriculationNumber',
        'givenName',
        'sn',
        'swissEduPersonGender',
        'ou'
    ]

    def _escape(self, query):
        """LDAP-style excape symbols for some special characters.

        According to the ldap3 documentation.
        """
        replacements = {
            '*': r'\\2A',
            '(': r'\\28',
            ')': r'\\29',
            '\\': r'\\5C',
            chr(0): r'\\00'
        }

        return re.sub(
            '.',
            lambda m: replacements.get(m.group(), m.group()),
            query)

    def _filter_data(self, data):
        """Utility to filter ldap data.

        It will take all fields relevant for a user update and map them
        to the correct fields as used by our api.

        Also sets the _ldap_updated field to utcnow.

        Sets default for send_newsletter to True.

        Args:
            data: One single item from LDAP (i.e. data for one student)

        Returns:
            dict: A dict with data as needed by our API, containing:
                _ldap_updated
                firstname,
                lastname,
                nethz,
                legi,
                gender,
                department,
                membership,
                It does NOT contain, password, email and RFID
        """
        res = {
            'nethz': data['cn'][0],
            'legi': data['swissEduPersonMatriculationNumber'],
            'firstname': data['givenName'][0],
            'lastname': data['sn'][0]
        }
        res['email'] = '%s@ethz.ch' % res['nethz']
        res['gender'] = \
            u"male" if int(data['swissEduPersonGender']) == 1 else u"female"

        if ('D-ITET' in data['ou']):
            res['department'] = u"itet"
        elif ('D-MAVT' in data['ou']):
            res['department'] = u"mavt"
        else:
            res['department'] = u"other"

        # ou contains all organisation units. Check if it contains a unit which
        # is associated with the organisation: Will be false if no intersection
        # The implementation with set intersection yields the fastest result
        ou_list = current_app.config['LDAP_MEMBER_OU_LIST']
        is_member = bool(set(data['ou']).intersection(set(ou_list)))

        if (('VSETH Mitglied' in data['ou']) and is_member):
            res['membership'] = u"regular"
        else:
            res['membership'] = u"none"

        return res

    def authenticate_user(self, cn, password):
        """Try to authenticate a user with ldap.

        If successful it queries the data, parses it and returns it.
        If either auth fails or user doesnt exist it returns None.

        Args:
            cn (string): the common name to search ldap for -> the nethz name
            password (string): the user password (plaintext)

        Returns:
            bool: True if successful, False otherwise
        """
        if self.ldap.authenticate(cn, password):
            return True  # success!
        else:
            # Auth with ldap failed
            return False

    def find_user(self, cn):
        """Query ldap by common name. Return filtered data or None.

        Args:
            cn (str): Common name of a user

        Returns:
            dict: ldap data of user if found, None otherwise
        """
        result = list(self.ldap.search("(cn=%s)" % self._escape(cn),
                                       attributes=self.LDAP_ATTR))

        if result:
            return self._filter_data(result[0])

    def find_members(self):
        """Query ldap for all organisation members.

        Returns:
            generator: generator of dicts with filtered ldap data.
        """
        # Create query: VSETH member and part of any of member ou
        ou_items = (u"(ou=%s)" % self._escape(item) for item in
                    current_app.config['LDAP_MEMBER_OU_LIST'])
        query_string = u"(& (ou=VSETH Mitglied) (| %s) )" % ''.join(ou_items)

        results = self.ldap.search(query_string, attributes=self.LDAP_ATTR)

        return (self._filter_data(item) for item in results)

    def create(self, data):
        """Add user to db.

        Args:
            data (dict): The ldap user data

        Returns:
            dict: The new user
        """
        with admin_permissions():
            return post_internal('users', data, skip_validation=True)[0]

    def compare_and_update(self, db_data, ldap_data):
        """Compare ldap data to user in db and patch if needed.

        Args:
            db_data (dict): User data from the database
            ldap_data (dict): User data from ldap

        Returns:
            dict: The updated user (or original user if nothing is updated)
        """
        # Compare to find only necessary updates
        updates = {
            key: value for (key, value) in ldap_data.items() if
            ldap_data[key] != db_data.get(key)
        }

        # Membership and Mail will not be overwritten
        updates.pop('email', None)
        if db_data.get('membership') != u"none":
            updates.pop('membership', None)

        if updates:
            with admin_permissions():
                return patch_internal('users',
                                      updates,
                                      skip_validation=True,
                                      _id=db_data['_id'])[0]
        else:
            return db_data  # No updates

    def sync_one(self, cn):
        """Synrchonize ldap and database for a single user.

        Query ldap by common name (cn).

        If user is found and in our database: Update if necessary.
        If user is found and not in database: Import.

        Otherwise do nothing.

        cn will be properly excaped for ldap.

        Args:
            cn (string): Common name of user.

        Returns:
            dict: Updated user data, None if user not found in ldap.
        """
        ldap_data = self.find_user(cn)
        if ldap_data is None:
            return

        user = current_app.data.driver.db['users'].find_one({'nethz': cn})
        if user:
            user = self.compare_and_update(user, ldap_data)
        else:
            user = self.create(ldap_data)

        return user

    def sync_all(self):
        """Query the ETH LDAP for all our members. Adds nonexisting ones to db.

        Updates existing ones if ldap data has changed.

        Args:
            user: the ldap user. must be privileged to search for all ldap users
            password: the password for the ldap user
            session: a database session
            ou_list: list of assigned organisational units in ldap

        Returns:
            tuple: First element is the number of new users,
                Second element the number of updated users
                Third element a list of users that failed to update (if any)
        """
        ldap_data = self.find_members()
        ldap_dict = {member['nethz']: member for member in ldap_data}

        # Find users already in database
        users = current_app.data.driver.db['users']
        query = {'nethz': {'$in': list(ldap_dict.keys())}}
        projection = {
            'firstname': 1,
            'lastname': 1,
            'nethz': 1,
            'legi': 1,
            'gender': 1,
            'department': 1,
            'membership': 1,
        }
        existing_users = users.find(query, projection)
        synced_users = []

        for user in existing_users:
            # Remove all updated users from ldap dict with pop
            updated = self.compare_and_update(user,
                                              ldap_dict.pop(user['nethz']))
            synced_users.append(updated)

        # All entries left in the ldap dict need to be created
        for (nethz, user) in ldap_dict.items():
            new = self.create(user)
            synced_users.append(new)

        return synced_users

ldap_connector = LdapConnector()
"""The ldap connector.

Import this to query ldap. Don't forget to call ``init_app(app)`` in the
factory function.
"""
