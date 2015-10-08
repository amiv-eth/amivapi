# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
All ldap functions are collected here.

Contains a connector class designed for use with the app and a sync function
designed for cron jobs or manual imports
"""
from datetime import datetime as dt
import re

from flask import current_app as app
from eve.utils import document_etag
from amivapi.models import User
from sqlalchemy import exc

from nethz import ldap

# The LDAP attributes we need for the api
LDAP_ATTR = [
    'cn',
    'swissEduPersonMatriculationNumber',
    'givenName',
    'sn',
    'swissEduPersonGender',
    'ou'
]


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

    return res


def _changed(db_user, ldap_user):
    """ Compare user from db with ldap data """
    for key in ldap_user:
        if getattr(db_user, key) != ldap_user[key]:
            return True
    return False


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

            raw_data = self.ldap.search(
                "(cn=%s)" % _escape(cn),
                attributes=LDAP_ATTR
            )[0]
            data = _filter_data(raw_data, app.config['LDAP_MEMBER_OU_LIST'])

            return data  # success!

        # Auth with ldap failed
        app.logger.debug("User with cn '%s' could not be authorized" % cn)
        return None


def ldap_synchronize(user, pw, session, ou_list):

    # Part 1: Get data from ldap
    connector = ldap.AuthenticatedLdap(user, pw)

    # Build the query
    # Member? VSETH necessary, then any of the fields
    query_string = u"(& (ou=VSETH Mitglied)(| "
    for item in ou_list:
        query_string += u"(ou=%s)" % _escape(item)  # Items contain braces
    query_string += u" ) )"

    results = connector.search(query_string, attributes=LDAP_ATTR)

    res_dict = {item['cn'][0]: item for item in results}

    res_set = set(res_dict.keys())

    # Part 2: Get data from db
    users = session.query(User).all()

    u_set = set([item.nethz for item in users])

    # Part 3: Import users not yet in database
    new = res_set.difference(u_set)  # items in results which are not in users

    failed = {
        'bad_ldap_data': [],
        'failed_import': [],
        'failed_update': []
    }

    n_new = 0
    for nethz in new:
        try:
            filtered = _filter_data(res_dict[nethz], ou_list)
            user = User(
                _author=0,
                _created=dt.utcnow(),
                _updated=dt.utcnow(),
                _etag=document_etag(filtered),
                username=filtered['nethz'],
                email="%s@ethz.ch" % filtered['nethz'],
                **filtered  # Rest of the daa
            )
            session.add(user)
            try:
                session.commit()
                n_new += 1
            except exc.SQLAlchemyError:
                failed['failed_import'] += user
                session.rollback()
        except KeyError:  # A key error will happen if ldap data is incomplete
            failed['bad_ldap_data'] += res_dict[nethz]

    # Part 4: Update users already in database
    old = res_set.intersection(u_set)

    user_query = session.query(User)
    n_old = 0
    for nethz in old:
        try:
            filtered = _filter_data(res_dict[nethz], ou_list)
            user = user_query.filter_by(nethz=nethz)
            userdata = user.one()

            # Is anything different?
            if _changed(userdata, filtered):
                # No downgrade of membership
                if userdata.membership is not "none":
                    filtered.pop('membership')

                user.update(filtered)
                try:
                    session.commit()
                    n_old += 1
                except exc.SQLAlchemyError:
                    failed['failed_update'] += filtered
                    session.rollback()
        except KeyError:
            failed['bad_ldap_data'] += res_dict[nethz]

    return (n_new, n_old, failed)
