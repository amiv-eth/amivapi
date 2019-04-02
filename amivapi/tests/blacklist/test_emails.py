# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for blacklist resource."""

from amivapi.tests.utils import WebTest
from datetime import datetime
from freezegun import freeze_time


class BlacklistEmailTest(WebTest):
    """Test blacklist emails.

    Everytime a user is added or removed from the blacklist, he should receive
    an email.
    """

    def test_receive_email_on_new_entry_with_price(self):
        """Test that a user receives an email if he is added to the blacklist"""
        # Create a user
        self.load_fixture({'users': [{'_id': 24 * "0", 'email': "bla@bla.bl"}]})
        data = {
            'user': 24 * "0",
            'reason': "Test",
            'price': 550,
            'start_time': "2019-03-29T00:00:00Z",
            'end_time': "2019-03-30T00:00:00Z",
        }
        self.api.post("/blacklist", data=data, token=self.get_root_token(),
                      status_code=201)

        # Look for sent out mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        expected_text = (
            "You have been blacklisted for the following reason:\n\nTest"
            "\n\nThis means that you cannot register for any new amiv events! "
            "To get removed from the blacklist, you have to pay 5.50 CHF\n\n"
            "If you think that this is an error, don't hesitate to contact "
            "bouncer@amiv.ethz.ch\n\nBest Regards,\nAMIV"
        )
        self.assertEqual(mail['text'], expected_text)

    def test_receive_email_on_new_entry_wo_price(self):
        """Test if a user receives an email if he is added to the blacklist."""
        # Create a user
        self.load_fixture({'users': [{'_id': 24 * "0", 'email': "bla@bla.bl"}]})
        data = {
            'user': 24 * "0",
            'reason': "Test",
            'start_time': "2019-03-29T00:00:00Z",
            'end_time': "2019-03-30T00:00:00Z",
        }
        self.api.post("/blacklist", data=data, token=self.get_root_token(),
                      status_code=201)

        # Check mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        expected_text = (
            "You have been blacklisted for the following reason:\n\nTest"
            "\n\nThis means that you cannot register for any new amiv "
            "events!\n\nIf you think that this is an error, don't hesitate to "
            "contact bouncer@amiv.ethz.ch\n\nBest Regards,\nAMIV"
        )
        self.assertEqual(mail['text'], expected_text)

    def test_receive_email_on_patch(self):
        """Test if a user receives a mail if one of his entries is resolved."""
        user_id = 24 * '0'
        blacklist_id = 24 * '1'

        # Create user and blacklist entry
        self.load_fixture({'users': [{'_id': user_id, 'email': "bla@bla.bl"}]})
        r = self.load_fixture({
                'blacklist': [{
                    '_id': blacklist_id,
                    'user': user_id,
                    'reason': "Test1",
                    'end_time': datetime(2017, 1, 1)}]
            })

        etag = r[0]['_etag']

        patch = {'reason': "Test2"}
        header = {'If-Match': etag}
        with freeze_time(datetime(2017, 1, 2)):
            r = self.api.patch("/blacklist/%s" % blacklist_id, data=patch,
                               headers=header, token=self.get_root_token(),
                               status_code=200)

        # Check mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        expected_text = (
            "Congratulations, your blacklist entry with the following reason "
            "has been removed:\n\nTest1\n\nBest Regards,\nAMIV"
        )
        self.assertEqual(mail['text'], expected_text)

    def test_receive_email_on_delete(self):
        """Test if a user receives an email if one of his entries is deleted."""
        user_id = 24 * '0'
        blacklist_id = 24 * '1'

        # Create user and blacklist entry
        self.load_fixture({'users': [{'_id': user_id, 'email': "bla@bla.bl"}]})
        r = self.load_fixture({
                'blacklist': [{
                    '_id': blacklist_id,
                    'user': user_id,
                    'reason': "Test1",
                    'end_time': datetime(2017, 1, 1)}]
            })

        etag = r[0]['_etag']

        header = {'If-Match': etag}
        r = self.api.delete("/blacklist/%s" % blacklist_id,
                            headers=header, token=self.get_root_token(),
                            status_code=204)

        # Check mail
        mail = self.app.test_mails[1]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        expected_text = (
            "Congratulations, your blacklist entry with the following reason "
            "has been removed:\n\nTest1\n\nBest Regards,\nAMIV"
        )
        self.assertEqual(mail['text'], expected_text)
