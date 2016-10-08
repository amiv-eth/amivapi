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
        current_app.logger.debug(
            "Sychronizing user '%s' with LDAP..." % cn)

        # cn is unique, will either be None or contain a list with one item
        raw_ldap_data = self.ldap.search("(cn=%s)" % self._escape(cn),
                                         attributes=self.LDAP_ATTR)

        if raw_ldap_data is None:
            current_app.logger.debug("LDAP entry not found. Aborting...")
            return None

        current_app.logger.debug("LDAP entry found.")

        ldap_data = self._filter_data(raw_ldap_data[0])

        # Create or update user
        user = current_app.data.find_one('users', None, nethz=cn)

        if user is not None:
            current_app.logger.debug(
                "Database entry found. (id=%s)" % user['id'])

            # Membership status will only be upgraded automatically
            # If current Membership is not none ignore the ldap result
            if user['membership'] is not None:
                del ldap_data['membership']

            # First element of response tuple is data
            patched = patch_internal('users',
                                     ldap_data,
                                     skip_validation=True,
                                     id=user['id'])[0]
            current_app.logger.debug(
                "Database entry updated.")
            return patched
        else:
            current_app.logger.debug("Database entry not found.")

            # Set Mail now
            ldap_data['email'] = "%s@ethz.ch" % ldap_data['nethz']

            # First element of response tuple is data
            posted = post_internal('users',
                                   ldap_data,
                                   skip_validation=True)[0]

            current_app.logger.debug("LDAP: user '%s' was created." % cn)
            return posted

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
        # Build the query
        # Member? VSETH necessary, then any of the fields
        query_string = u"(& (ou=VSETH Mitglied)(| "
        for item in current_app.config['LDAP_MEMBER_OU_LIST']:
            query_string += u"(ou=%s)" % self._escape(item)
        query_string += u" ) )"

        # Users from LDAP (Turn result into dict for easier handling later)
        results = self.ldap.search(query_string, attributes=self.LDAP_ATTR)
        results = {item['cn'][0]: item for item in results}
        ldap_set = set(results.keys())

        # Users from db
        users = (current_app.data.driver.session.query(User)
                 .filter(User.nethz.isnot(None)).all())
        users = {item.nethz: item for item in users}
        db_set = set(users.keys())

        failed = []

        # Import users not yet in database
        new = ldap_set.difference(db_set)

        n_new = 0
        for nethz in new:
            try:
                ldap_data = self._filter_data(results[nethz])

                # Set Mail now
                ldap_data['email'] = "%s@ethz.ch" % ldap_data['nethz']

                post_internal("users", ldap_data, skip_validation=True)

                n_new += 1
            except KeyError:
                failed += results[nethz]

        # Update users already in database
        old = ldap_set.intersection(db_set)

        n_old = 0
        for nethz in old:
            try:
                ldap_data = self._filter_data(results[nethz])
                user_data = current_app.data.find_one("users", None,
                                                      nethz=nethz)

                # Is anything different?
                if self._changed(user_data, ldap_data):
                    # No downgrade of membership
                    if ldap_data['membership'] is not "none":
                            ldap_data.pop('membership')

                patch_internal('users',
                               ldap_data,
                               skip_validation=True,
                               id=user_data['id'])
                n_old += 1
            except KeyError:
                failed += results[nethz]

        return (n_new, n_old, failed)

ldap_connector = LdapConnector()
"""The ldap connector.

Import this to query ldap. Don't forget to call ``init_app(app)`` in the
factory function.

Remark: If this was a real flask extension, this would not be here.
    Rather somewhere in your code you would create this object and import it
    everywhere else. But since this is all in our code, we just create it here.

    Maybe this could be done better? Create this instance in bootstrap.py?
"""
