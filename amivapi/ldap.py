# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
All ldap functions are collected here.

Contains a connector class designed for use with the app and a sync function
designed for cron jobs or manual imports
"""
import re

from flask import current_app
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from nethz import ldap

from amivapi.utils import admin_permissions


class LdapConnector():
    """LDAP Connector.

    With all functions required for the app object.
    Can authenticate a user and provide up-to-date information for ETH LDAP.

    The app config needs to contain the following keys:
        LDAP_USER
        LDAP_PASS
        LDAP_MEMBER_OU_LIST

    All functions provide a lot of debug logging.

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

    def _changed(self, db_user, ldap_user):
        """Compare user from db with ldap data.

        The user can have more data than what ldap provides, therefore it just
        checks if the values set by ldap are changed.
        """
        for key in ldap_user:
            if db_user['key'] != ldap_user[key]:
                return True
        return False

    def _escape(self, query):
        r"""LDAP-style excape symbols for some special characters.

        From the docs of ldap3:
        If the search filter contains the following characters you must use the
        relevant escape ASCII sequence, as per RFC4515 (section 3):
        ‘*’ -> ‘\\2A’,
        ‘(‘ -> ‘\\28’,
        ‘)’ -> ‘\\29’,
        ‘\’ -> ‘\\5C’,
        chr(0) -> ‘\\00’

        Helper function to achieve this.
        """
        replacements = {
            '*': r'\\2A',
            '(': r'\\28',
            ')': r'\\29',
            '\\': r'\\5C',  # r as string flag doesnt work with \'
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
                firstname,
                lastname,
                nethz,
                legi,
                gender,
                department,
                membership,
                It does NOT contain, password, email and RFID
        """
        res = {}
        res['nethz'] = data['cn'][0]
        res['legi'] = data['swissEduPersonMatriculationNumber'][0]
        res['firstname'] = data['givenName'][0]
        res['lastname'] = data['sn'][0]
        gendermap = {'1': u"male", '2': u"female"}
        # If gender not specified, the person will be a woman :)
        res['gender'] = gendermap[data['swissEduPersonGender'][0]]
        # res['email'] = data['mail'][0]  TODO

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
            password (string): the nethz password

        Returns:
            bool: True if successful, False otherwise
        """
        if self.ldap.authenticate(cn, password):
            current_app.logger.debug(
                "Ldap-auth for user with cn '%s' successful." % cn)
            return True  # success!
        else:
            # Auth with ldap failed
            current_app.logger.debug(
                "Ldap-auth for user with cn '%s' failed." % cn)
            return False

    def find_user(self, cn):
        """Query ldap by common name. Return filtered data or None.

        Args:
            cn (str): Common name of a user

        Returns:
            dict: ldap data of user if found, None otherwise
        """
        result = self.ldap.search("(cn=%s)" % self._escape(cn),
                                  attributes=self.LDAP_ATTR)

        if result is not None:
            return self._filter_data(result)

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
        """Set mail for user and add to db.

        Args:
            data (dict): The ldap user data

        Returns:
            dict: The new user
        """
        data['email'] = "%s@ethz.ch" % data['nethz']

        with admin_permissions():
            return post_internal('users', data, skip_validation=True)[0]

    def update(self, db_data, ldap_data):
        """Compare ldap data to user in db and patch if needed.

        Args:
            db_data (dict): User data from the database
            ldap_data (dict): User data from ldap

        Returns:
            dict: Everything that was actually patched
        """
        # COMPARE ETC self._changed(user_data, ldap_data)
        # Membership will only be upgraded from "None"
        if db_data['membership'] is not "none":
            del ldap_data['membership']

        with admin_permissions():
            return patch_internal('users',
                                  ldap_data,
                                  skip_validation=True,
                                  id=db_data['id'])[0]

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
        current_app.logger.debug("Sychronizing user '%s' with LDAP..." % cn)

        ldap_data = self.find_user(cn)

        if ldap_data is None:
            current_app.logger.debug("LDAP entry not found. Aborting...")
            return

        current_app.logger.debug("LDAP entry found.")

        # Create or update user
        user = current_app.data.driver.db['users'].find_one({'nethz': cn})

        if user:
            current_app.logger.debug(
                "Database entry found. (id=%s)" % user['id'])
            user = self.update(user, ldap_data)
        else:
            current_app.logger.debug("Database entry not found.")
            user = self.create(ldap_data)

        current_app.logger.debug("User with nethz '%s' was synchronized." % cn)
        return user

    def sync_all(self):
        """Query the ETH LDAP for all our members. Adds nonexisting ones to db.

        Updates existing ones if ldap data has changed.

        Returns:
            tuple: First element is the number of new users,
                Second element the number of updated users
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

        for user in existing_users:
            # Remove all updated users from ldap dict with pop
            updates = self.update(user, ldap_dict.pop(user['nethz']))
            if updates:
                current_app.logger.info("User with nethz '%s' was updated." %
                                        user['nethz'])

        # All entries left in the ldap dict need to be created
        for (nethz, user) in ldap_dict.items():
            self.create(user)
            current_app.logger.info("User with nethz '%s' was created." %
                                    nethz)

ldap_connector = LdapConnector()
"""The ldap connector.

Import this to query ldap. Don't forget to call ``init_app(app)`` in the
factory function.

Remark: If this was a real flask extension, this would not be here.
    Rather somewhere in your code you would create this object and import it
    everywhere else. But since this is all in our code, we just create it here.

    Maybe this could be done better? Create this instance in bootstrap.py?
"""
