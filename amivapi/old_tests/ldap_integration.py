# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Integration Tests for LDAP.

The API can connect to ETH LDAP to process login and update user data.

Since we don't have access to test accounts for LDAP you need to specify
valid ETH credentials in the environment variables.

There set them first:

Bash:
> export ldap_test_nethz="YOUR_NETHZ"
> export ldap_test_pass="YOUR_PASSWORD"

Windows PowerShell:
> $env:ldap_test_nethz="YOUR_NETHZ_HERE"
> $env:ldap_test_pass="YOUR_PASSWORD"

Next make sure the config.cfg contains:

ENABLE_LDAP = False
LDAP_USER = 'YOUR_LDAP_ACCOUNT'
LDAP_PASS = 'YOUR_LDAP_ACCOUNT_PASSWORD'

(you can use manage.py for this of course)

Then run the test with

> nosetests -s amivapi/tests/test_ldap_integration.py

You need the -s flag to get the full printout. You will see the imported data
and have to verify yourself if this is correct.
"""


from amivapi.tests.utils import WebTest
from amivapi.ldap import ldap_connector

from os import getenv


class LdapIntegrationTest(WebTest):
    """Tests for LDAP connection."""

    def setUp(self, *args, **kwargs):
        """Extended setUp.

        Load environment variables and test general ldap connection.
        """
        super(LdapIntegrationTest, self).setUp(*args, **kwargs)
        self.nethz = getenv('ldap_test_nethz', "")
        self.password = getenv('ldap_test_pass', "")
        if not(self.nethz and self.password):
            self.app.logger.debug("You need to specify 'ldap_test_nethz' and "
                                  "'ldap_test_pass' in the environment "
                                  "variables!")

        with self.app.app_context():
            try:
                # Search for something random to see if the connection works
                ldap_connector.authenticate_user("bla", "blorg")
            except Exception as e:
                self.app.logger.debug("The LDAP query failed. Make sure that "
                                      "you are in the eth network or have "
                                      "VPN enabled to find the servers.")
                self.app.logger.debug("Exception message below:")
                self.app.logger.debug(e)

    def _fetch_user(self):
        return self.db['users'].find_one({'nethz': self.nethz})

    def _update_user(self, updates):
        return self.db['users'].update({'nethz': self.nethz}, updates)

    def test_ldap_auth(self):
        """Test auth via LDAP.

        Login with real credentials to test LDAP
        """
        # Make sure that user with nethz name does not exist in db
        self.assertNone(self._fetch_user())

        # Login -> this will trigger ldap
        self.api.post("/sessions", data={
            'user': self.nethz,
            'password': self.password,
        }, status_code=201)  # .json

        # Make sure the user exists now
        self.assertNotNone(self._find_by_nethz(self.nethz))

        user = self._find_by_nethz(self.nethz)
        gender = self._find_by_nethz(self.nethz)['gender']

        if gender == u"male":
            new_gender = u"female"
        else:
            new_gender = u"male"

        # Test if ldap data doesn't equal database
        # Change gender and membership status
        self._update_user({'gender': new_gender, 'membership': "honorary"})

        # Now the data should be different (duh.)
        get_1 = self._find_by_nethz(self.nethz)
        self.assertNotEqual(get_1.gender, gender)
        self.assertEqual(get_1.membership, "honorary")

        # Log in again, this should cause the API to sync with LDAP again
        self.api.post("/sessions", data={
            'user': self.nethz,
            'password': self.password,
        }, status_code=201)

        # Now gender should be the same again
        # But the membership status should not downgraded
        get_2 = self._find_by_nethz(self.nethz)
        self.assertEqual(get_2['gender'], gender)
        self.assertEqual(get_2['membership'], "honorary")

        # Important point: Since we have no "test-dummy", we are working with
        # real data that we can't predict. All the above is only good if the
        # correct data was imported, which has to be checked manually
        print("\nPlease verify that the imported data is correct and "
              "complete:")
        for key in user:
            if key[0] != '_':
                print("%s: %s" % key, user['key'])

    def test_password_not_stored(self):
        """Test that passwords are not stored.

        If login is handled by ldap there is no reason we should store the
        password.
        """
        # Log in
        user = self.api.post("/sessions", data={
            'user': self.nethz,
            'password': self.password,
        }, status_code=201).json

        # Check database
        user = self.db.query(models.User).filter_by(nethz=self.nethz).one()
        self.assertIsNone(user.password)

    def test_cron_sync(self):
        """Test ldap sync for cronjob."""
        # Save number of users in db (should be root and anonymous)
        n_previous = self.db.query(models.User).count()

        # Do the ldap sync
        with self.app.test_request_context():
            res = ldap_connector.sync_all()

        # Assert some users actually were imported:
        self.assertTrue(res[0] > n_previous)

        # Assert no user was updated
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
        with self.app.test_request_context():
            res = ldap_connector.sync_all()

        # No imports, one update:
        self.assertTrue(res[0] == 0)
        self.assertTrue(res[1] == 1)

        # user has been changed back
        self.assertFalse(user.lastname == wrongname)
