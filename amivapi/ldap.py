# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
Create ldap shizzle
"""
from datetime import datetime as dt
import re

from flask import current_app as app
from eve.utils import document_etag
from amivapi.models import User

from nethz import ldap


def _escape(query):
    """
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
        '*': r'\2A',
        '(': r'\28',
        ')': r'\29',
        '\\': r'\5C',  # r as string flag doesnt work with \'
        chr(0): r'\00'
    }

    return re.sub(
        '.',
        lambda m: replacements.get(m.group(), m.group()),
        query)


def _filter_data(data, ou_list):
    """ Utility to filter ldap data. It will take all fields relevant for
    a user update and map them to the correct fields as used by our api.

    Also sets the _ldap_updated field to utcnow

    :param data: One single item from LDAP (i.e. data for one student)
    :param ou_list: List of organisational units to consider for membership
    :returns: A dict with data as needed by our API, containing:
              _ldap_updated
              firstname,
              lastname,
              nethz,
              legi,
              gender,
              department,
              membership
              It does NOT contain username, password, email and RFID
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
    is_member = bool(set(data['ou']).intersection(set(ou_list)))

    if (('VSETH Mitglied' in data['ou']) and is_member):
        res['membership'] = u"regular"
    else:
        res['membership'] = u"none"

    # Set datetime for this update
    res['_ldap_updated'] = dt.utcnow()

    return res


class LdapConnector():
    """
    the ldap connector with all functions required for the app.
    Can authenticate a user and provide up-to-date information
    """
    def __init__(self, user, pw):
        """
        :param user: the ldap user. must be privileged to search for all ldap
        users
        :param pw: the password for the ldap user
        """
        self.ldap = ldap.AuthenticatedLdap(user, pw)

    def check_user(self, cn, pw):
        """
        Tries to authenticate a user with ldap.
        If successful it queries the data, parses it and returns it.
        If either auth fails or user doesnt exist it returns None.

        :param cn: the common name to search ldap for -> the nethz name
        :param pw: the password

        :returns: None or a dict with updated data
        """
        # Step 1: Try to authorize
        if self.ldap.authenticate(cn, pw):
            # Step 2: Fetch new data
            # Since auth was successful the user has to exist
            # Since the common name is unique it is also safe to just use the
            # first result
            app.logger.debug("Successful ldap auth for user with cn '%s'" % cn)

            raw_data = self.ldap.search("(cn=%s)" % _escape(cn))[0]
            data = _filter_data(raw_data, app.config['LDAP_MEMBER_OU_LIST'])

            return data  # success!

        # Auth with ldap failed
        app.logger.debug("User with cn '%s' could not be authorized" % cn)
        return None


class LdapSynchronizer():
    """
    a specialised ldap connector for database updates.
    the synchronizer will add users from ldap to our database if missing and
    can update existing users
    """
    def __init__(self, user, pw, session, ou_list, n_import, n_update):
        """
        :param user: the ldap user. must be privileged to search for all ldap
        users
        :param pw: the password for the ldap user
        :param session: the database session
        :param ou_list: organisational units to consider for membership
        :param n_import: maximum number of new imports from ldap
        :param n_update: maximum number of users that will be updated
        """
        self.ldap = ldap.AuthenticatedLdap(user, pw)

        self.session = session

        self.ou_list = ou_list

        self.n_import = n_import
        self.n_update = n_update

    def user_import(self):
        """
        queries ldap for users not existing in the database.
        returns a maximum of results as specified in the app config

        :returns: Number of imported users
        """
        # Build the query
        # Base: is member? VSETH necessary, then any of the fields
        base = u"(ou=VSETH Mitglied)"

        ou = ""
        for item in self.ou_list:
            ou += u"(ou=%s)" % _escape(item)  # Items contain braces

        if len(self.ou_list) > 1:
            ou = u"(| %s )" % ou

        # Now exclude everyone who is in the db - they will be taken care of in
        # ldap_sync
        users = self.session.query(User).filter(User.nethz.isnot(None)).all()
        if users:
            ext = u""
            for user in users:
                ext += u"(!(cn=%s))" % _escape(user.nethz)  # just to be sure

            ldap_query = "(&%s%s%s)" % (ext, ou, base)
        else:
            # No users, base is whole query
            ldap_query = "(&%s%s)" % (base, ou)

        result = self.ldap.search(ldap_query, limit=self.n_import)

        done = 0
        for item in result:
            try:
                filtered = _filter_data(item, self.ou_list)
                user = User(
                    _author=0,
                    _created=dt.utcnow(),
                    _updated=dt.utcnow(),
                    _etag=document_etag(filtered),
                    username=filtered['nethz'],
                    email="%s@ethz.ch" % filtered['nethz'],
                    **filtered  # Rest of the daa
                )
                self.session.add(user)
                self.session.commit()
                done += 1
            except:  # If anything is broken with the ldap data just ignore it.
                self.session.rollback()

        return done

    def user_update(self):
        """
        Select the n users from the database which have been updated last and
        query ldap to see if any information has changed.

        If there has never been an LDAP update, _ldap_updated will be set to
        None - those will be tried to be updated first

        :returns: Number of updated users
        """
        # Get n users with nethz name not Null
        users = (
            self.session.query(User)
            .filter(User.nethz.isnot(None))
            .order_by(User._ldap_updated)
            [:self.n_update])

        if len(users) == 0:
            return 0  # Nothing to update

        # Create a dict for easy assignment later
        # Ignore users without nethz since they can not be queried

        # Prepare ldap query
        ldap_query = "(|"
        for user in users:
            ldap_query += "(cn=%s)" % _escape(user.nethz)
        ldap_query += ")"

        # Query ldap
        ldap_res_raw = self.ldap.search(ldap_query)
        # Put in dictionary with nethz as key for access
        ldap_res = {}
        for item in ldap_res_raw:
            filtered = _filter_data(item, self.ou_list)
            ldap_res[filtered['nethz']] = filtered

        # Now update users
        query_all = self.session.query(User)
        for user in users:
            # Filter for user
            query = query_all.filter_by(nethz=user.nethz)
            if user.nethz in ldap_res.keys():
                # No downgrade of membership
                if user.membership is not "none":
                    ldap_res[user.nethz].pop('membership')

                query.update(ldap_res[user.nethz])
            else:
                # Still set _synchronized
                query.update({'_ldap_updated': dt.utcnow()})

        # Finishing move
        self.session.commit()

        return len(ldap_res_raw)
