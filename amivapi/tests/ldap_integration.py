# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from amivapi.tests import util
from amivapi import models
from amivapi.ldap import ldap_synchronize

from sqlalchemy import exists

import re
from os import getenv
from copy import copy


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
        print("\nPlease verify that the imported data is correct:")
        data = user.__table__.columns._data
        for key in data.keys():
            if re.match('^_.+$', key):
                continue  # Exclude meta fields
            print("%s: %s" % (key, getattr(user, key)))

    def test_cron_sync(self):
        # Assert that only 2 users are in the db (root and anonymous)
        self.assertTrue(self.db.query(models.User).count() == 2)

        # Do the ldap sync
        res = ldap_synchronize(self.app.config['LDAP_USER'],
                               self.app.config['LDAP_PASS'],
                               self.db,
                               self.app.config['LDAP_MEMBER_OU_LIST'])

        # Check that some users actually were imported:
        self.assertTrue(res[0] > 0)

        # Check if no user was updated
        self.assertTrue(res[1] == 0)

        # Check that the users are now actually in the db
        self.assertTrue(self.db.query(models.User).count() == res[0] + 2)

        # Change a random user
        user = (self.db.query(models.User)
                .filter(models.User.nethz.isnot(None)).all())[0]

        wrongname = u"NoLastNameLookslikethis"

        user.lastname = wrongname

        self.db.commit()

        # sync again
        res = ldap_synchronize(self.app.config['LDAP_USER'],
                               self.app.config['LDAP_PASS'],
                               self.db,
                               self.app.config['LDAP_MEMBER_OU_LIST'])

        # No imports, one update:
        self.assertTrue(res[0] == 0)
        self.assertTrue(res[1] == 1)

        # user has been changed back
        self.assertFalse(user.lastname == wrongname)
