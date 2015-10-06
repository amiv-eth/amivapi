# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util
from amivapi import models
from amivapi.ldap import LdapSynchronizer

from sqlalchemy import exists

import re
from datetime import datetime as dt
from os import getenv
from copy import copy

from time import sleep


class LdapIntegrationTest(util.WebTest):
    def setUp(self, *args, **kwargs):  # __init__(self, *args, **kwargs):
        super(LdapIntegrationTest, self).setUp(*args, **kwargs)
        self.username = getenv('ldap_test_user', "")
        self.password = getenv('ldap_test_pass', "")
        if not(self.username and self.password):
            self.app.logger.debug("You need to specify 'ldap_test_user' and "
                                  + "'ldap_test_pass' in the environment "
                                  + "variables!")

        with self.app.app_context():
            try:
                # Search for something random to see if the connection works
                self.app.ldap_connector.check_user("bla", "blorg")
            except Exception as e:
                self.app.logger.debug("The LDAP query failed. Make sure that "
                                      + "you are in the eth network or have "
                                      + "VPN enabled to find the servers.")
                self.app.logger.debug("Exception message below:")
                self.app.logger.debug(e)

    def test_ldap_auth(self):
        """
        Login with real credentials to test LDAP
        Has to be called with -uusername -ppassword
        """
        # Make sure that user with nethz name does not exist in db
        self.assertFalse(
            self.db.query(exists().where(models.User.nethz == self.username))
            .scalar())

        self.api.post("/sessions", data={
            'username': self.username,
            'password': self.password,
        }, status_code=201)  # .json

        # Make sure the user exists now
        self.assertTrue(
            self.db.query(exists().where(models.User.nethz == self.username))
            .scalar())

        user = self.db.query(models.User).filter_by(nethz=self.username).one()
        user = copy(user)

        gender = user.gender

        if gender == u"male":
            new_gender = u"female"
        else:
            new_gender = u"male"

        # Simulate that ldap data has chaned
        # Change gender and member status
        # Since from ldap we can only get regular or none as membership, we can
        # test this with setting it to honorary
        query = self.db.query(models.User).filter_by(nethz=self.username)
        query.update({'gender': new_gender, 'membership': "honorary"})
        self.db.commit()

        # Now the data should be different (duh.)
        get_1 = self.db.query(models.User).filter_by(nethz=self.username).one()
        self.assertNotEqual(get_1.gender, gender)
        self.assertEqual(get_1.membership, "honorary")

        # Log in again, this should cause the API to sync with LDAP again
        self.api.post("/sessions", data={
            'username': self.username,
            'password': self.password,
        }, status_code=201)

        # Now gender should be the same again
        # But the membership status should not downgraded
        get_2 = self.db.query(models.User).filter_by(nethz=self.username).one()
        self.assertEqual(get_2.gender, gender)
        self.assertEqual(get_2.membership, "honorary")

        # Important point: Since we have no "test-dummy", we are working with
        # real data that we can't predict. All the above is only good if the
        # correct data was imported, which has to be checked manually
        print("Please verify that the imported data is correct:")
        data = user.__table__.columns._data
        for key in data.keys():
            if re.match('^_.+$', key):
                continue  # Exclude meta fields
            print("%s: %s" % (key, getattr(user, key)))

    def assertSync(self, l_users, reference):
        for user in l_users:
            self.assertTrue(user._ldap_updated > reference)

    def assertNoSync(self, l_users, reference):
        for user in l_users:
            # No sinc at all or later
            if user._ldap_updated is not None:
                self.assertTrue(user._ldap_updated < reference)
            # If its None there has been no sync which is ok

    def test_cron_update(self):
        # Create the LDAP Synchronizer
        # With sync count 2
        ldap = LdapSynchronizer(self.app.config['LDAP_USER'],
                                self.app.config['LDAP_PASS'],
                                self.db,
                                self.app.config['LDAP_MEMBER_OU_LIST'],
                                0,
                                2)

        # Create a few fake users, 6 in total
        u_1 = self.new_user(nethz="Lalala@nonethz", _ldap_updated=None)
        u_2 = self.new_user(nethz="Lululu@nonethz", _ldap_updated=None)
        # Two without nethz, they should be skipped
        u_3 = self.new_user(nethz=None, _ldap_updated=None)
        u_4 = self.new_user(nethz=None, _ldap_updated=None)
        # Two with early date that should be synced first
        u_5 = self.new_user(nethz="Lololo@nonethz", _ldap_updated=dt.utcnow())
        u_6 = self.new_user(nethz="Lelele@nonethz", _ldap_updated=dt.utcnow())

        # Wait some time so the datetime is guaranteed later and create real
        # user
        # No legi given
        # Membership honorary
        sleep(1)
        u_real = self.new_user(nethz=self.username,
                               legi=None,
                               membership=u"honorary",
                               _ldap_updated=dt.utcnow())

        # Create reference time
        sleep(1)
        ref = dt.utcnow()

        ldap.user_update()

        # Now the first to should be synchronized, the others not
        # If yes, then the sync numer is correct and with no sync ever come
        # first
        self.assertSync([u_1, u_2], ref)
        self.assertNoSync([u_3, u_4, u_5, u_6, u_real], ref)

        # Sync again
        ldap.user_update()

        # Now if nethz with None are ignored, then u_3 and u_4 should still not
        # be synched
        # Now 5 and 6 should be synced
        self.assertSync([u_1, u_2, u_5, u_6], ref)
        self.assertNoSync([u_3, u_4, u_real], ref)

        # Last sync
        ldap.user_update()

        # Now u_real should have been synced, too.
        self.assertSync([u_1, u_2, u_5, u_6, u_real], ref)
        self.assertNoSync([u_3, u_4], ref)

        # No see if ldap import happened (e.g. legi not None anymore)
        # TODO: Maybe test all fields to be thorough?
        # But that membership is not downgraded and still honorary
        self.assertIsNotNone(u_real.legi)
        self.assertTrue(u_real.membership == u"honorary")

    def test_cron_import(self):
        # Create the LDAP Synchronizer
        # With import count 2
        ldap = LdapSynchronizer(self.app.config['LDAP_USER'],
                                self.app.config['LDAP_PASS'],
                                self.db,
                                self.app.config['LDAP_MEMBER_OU_LIST'],
                                5,
                                0)

        # Only 2 users in the db at this point
        # (root and anonymous)
        self.assertTrue(self.db.query(models.User).count() == 2)

        # Now 5 users more, 7 in total
        ldap.user_import()

        # Now try again to make sure the api does not try to import the same
        # users twice
        ldap.user_import()

        # Now 5 users more, 12 in total
        self.assertTrue(self.db.query(models.User).count() == 12)
