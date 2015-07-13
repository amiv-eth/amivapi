# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util
from amivapi import models, cron

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
            print("You need to specify 'ldap_test_user' and 'ldap_test_pass'" +
                  " in the environment variables!")

    def test_ldap_create(self):
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
            self.assertTrue(user._synchronized > reference)

    def assertNoSync(self, l_users, reference):
        for user in l_users:
            # No sinc at all or later
            if user._synchronized is not None:
                self.assertTrue(user._synchronized < reference)
            # If its None there has been no sync which is ok

    def test_cron(self):

        # Create a few fake users, 6 in total
        u_1 = self.new_user(nethz="Lalala@nonethz", _synchronized=None)
        u_2 = self.new_user(nethz="Lululu@nonethz", _synchronized=None)
        # Two without nethz, they should be skipped
        u_3 = self.new_user(nethz=None, _synchronized=None)
        u_4 = self.new_user(nethz=None, _synchronized=None)
        # Two with early date that should be synced first
        u_5 = self.new_user(nethz="Lololo@nonethz", _synchronized=dt.utcnow())
        u_6 = self.new_user(nethz="Lelele@nonethz", _synchronized=dt.utcnow())

        # Wait some time so the datetime is guaranteed later and create real
        # user
        # No legi given
        # Membership honorary
        sleep(1)
        u_real = self.new_user(nethz=self.username,
                               legi=None,
                               membership=u"honorary",
                               _synchronized=dt.utcnow())

        # Create reference time
        sleep(1)
        ref = dt.utcnow()

        # Make a fake config and set numer of sync targets to 2
        fake_config = {'LDAP_SYNC_COUNT': 2}

        cron.ldap_sync(self.db, fake_config, self.app.ldap_connector)

        # Now the first to should be synchronized, the others not
        # If yes, then the sync numer is correct and with no sync ever come
        # first
        self.assertSync([u_1, u_2], ref)
        self.assertNoSync([u_3, u_4, u_5, u_6, u_real], ref)

        # Sync again
        cron.ldap_sync(self.db, fake_config, self.app.ldap_connector)

        # Now if nethz with None are ignored, then u_3 and u_4 should still not
        # be synched
        # Now 5 and 6 should be synced
        self.assertSync([u_1, u_2, u_5, u_6], ref)
        self.assertNoSync([u_3, u_4, u_real], ref)

        # Last sync
        cron.ldap_sync(self.db, fake_config, self.app.ldap_connector)

        # Now u_real should have been synced, too.
        self.assertSync([u_1, u_2, u_5, u_6, u_real], ref)
        self.assertNoSync([u_3, u_4], ref)

        # No see if ldap import happened (e.g. legi not None anymore)
        # TODO: Maybe test all fields to be thorough?
        # But that membership is not downgraded and still honorary
        self.assertIsNotNone(u_real.legi)
        self.assertTrue(u_real.membership == u"honorary")
