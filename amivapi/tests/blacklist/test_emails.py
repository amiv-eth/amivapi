# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for blacklist resource."""

from amivapi.tests.utils import WebTest
from amivapi.cron import (
    run_scheduled_tasks
)
from datetime import datetime
from datetime import timedelta
from freezegun import freeze_time


class BlacklistEmailTest(WebTest):
    """Test blacklist emails.

    Everytime a user is added or removed from the blacklist, he should receive
    an email.
    """

    def test_receive_email_on_new_entry_with_price(self):
        """Test that a user receives an email if he is added to the blacklist"""
        # Create a user
        self.load_fixture({
                'users': [{
                    '_id': 24 * "0",
                    'firstname': 'Paula',
                    'email': "bla@bla.bl"
                }]
            })
        data = {
            'user': 24 * "0",
            'reason': "Test",
            'price': 550,
            'start_time': "2019-03-29T00:00:00Z",
        }
        self.api.post("/blacklist", data=data, token=self.get_root_token(),
                      status_code=201)

        # Look for sent out mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        self.assertIn(data['reason'], mail['text'])
        self.assertIn(data['reason'], mail['html'])
        self.assertIn("Paula", mail['text'])
        self.assertIn("Paula", mail['html'])
        self.assertIn("{:.2f}".format(data['price']/100), mail['text'])
        self.assertIn("{:.2f}".format(data['price']/100), mail['html'])

    def test_receive_email_on_new_entry_wo_price(self):
        """Test if a user receives an email if he is added to the blacklist."""
        # Create a user
        self.load_fixture({
                'users': [{
                    '_id': 24 * "0",
                    'firstname': 'Paula',
                    'email': "bla@bla.bl"
                }]
            })
        data = {
            'user': 24 * "0",
            'reason': "Test",
            'start_time': "2019-03-29T00:00:00Z",
        }
        self.api.post("/blacklist", data=data, token=self.get_root_token(),
                      status_code=201)

        # Check mail
        mail = self.app.test_mails[0]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        self.assertIn(data['reason'], mail['text'])
        self.assertIn(data['reason'], mail['html'])
        self.assertIn("Paula", mail['text'])
        self.assertIn("Paula", mail['html'])

    def test_receive_email_on_patch(self):
        """Test if a user receives a mail if one of his entries is resolved."""
        user_id = 24 * '0'
        blacklist_id = 24 * '1'

        # Create user and blacklist entry
        self.load_fixture({
                'users': [{
                    '_id': user_id,
                    'firstname': 'Paula',
                    'email': "bla@bla.bl"
                }]
            })
        r = self.load_fixture({
                'blacklist': [{
                    '_id': blacklist_id,
                    'user': user_id,
                    'reason': "Test1"}]
            })

        etag = r[0]['_etag']

        patch = {
            'user': user_id,
            'reason': "Test1",
            'end_time': '2017-01-01T00:00:00Z'
        }

        header = {'If-Match': etag}
        with freeze_time(datetime(2017, 6, 6)):
            r = self.api.patch("/blacklist/%s" % blacklist_id, data=patch,
                               headers=header, token=self.get_root_token(),
                               status_code=200)

        # Check mail
        mail = self.app.test_mails[1]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        self.assertIn(patch['reason'], mail['text'])
        self.assertIn(patch['reason'], mail['html'])
        self.assertIn('removed', mail['text'])
        self.assertIn('removed', mail['html'])

    def test_receive_email_on_delete(self):
        """Test if a user receives an email if one of his entries is deleted."""
        user_id = 24 * '0'
        blacklist_id = 24 * '1'

        # Create user and blacklist entry
        self.load_fixture({
                'users': [{
                    '_id': user_id,
                    'firstname': 'Paula',
                    'email': "bla@bla.bl"
                }]
            })
        r = self.load_fixture({
                'blacklist': [{
                    '_id': blacklist_id,
                    'user': user_id,
                    'reason': "Test1", }]
            })

        etag = r[0]['_etag']

        header = {'If-Match': etag}
        r = self.api.delete("/blacklist/%s" % blacklist_id,
                            headers=header, token=self.get_root_token(),
                            status_code=204)

        # Check mail
        mail = self.app.test_mails[1]
        self.assertEqual(mail['receivers'], 'bla@bla.bl')
        self.assertIn("Test1", mail['text'])
        self.assertIn("Test1", mail['html'])
        self.assertIn('removed', mail['text'])
        self.assertIn('removed', mail['html'])

    def test_receive_scheduled_email_on_create(self):
        """Test if a user receives an email if the end_time is reached"""
        with self.app.app_context(), freeze_time(
                "2017-01-01 00:00:00") as frozen_time:
            user_id = 24 * '0'
            blacklist_id = 24 * '1'

            # Create user and blacklist entry
            self.load_fixture({
                'users': [{
                    '_id': user_id,
                    'firstname': 'Paula',
                    'email': "bla@bla.bl"
                }]
            })
            self.load_fixture({
                'blacklist': [{
                    '_id': blacklist_id,
                    'user': user_id,
                    'reason': "Test1",
                    'end_time': datetime(2017, 1, 2)
                }]
            })

            run_scheduled_tasks()

            self.assertEqual(len(self.app.test_mails), 1)

            frozen_time.tick(delta=timedelta(days=1))

            run_scheduled_tasks()

            # Check mail
            mail = self.app.test_mails[1]
            self.assertEqual(mail['receivers'], 'bla@bla.bl')
            self.assertIn("Test1", mail['text'])
            self.assertIn("Test1", mail['html'])
            self.assertIn('removed', mail['text'])
            self.assertIn('removed', mail['html'])

    def test_receive_scheduled_email_on_patch(self):
        """Test if a user receives an email if the end_time is reached"""
        with self.app.app_context(), freeze_time(
                "2017-01-01 00:00:00") as frozen_time:
            user_id = 24 * '0'
            blacklist_id = 24 * '1'

            # Create user and blacklist entry
            self.load_fixture({
                'users': [{
                    '_id': user_id,
                    'firstname': 'Paula',
                    'email': "bla@bla.bl"
                }]
            })
            r = self.load_fixture({
                    'blacklist': [{
                        '_id': blacklist_id,
                        'user': user_id,
                        'reason': "Test1",
                        'end_time': "2017-01-02T00:00:00Z", }]
                })

            etag = r[0]['_etag']

            patch = {
                'user': user_id,
                'reason': "Test1",
                'end_time': '2017-01-03T00:00:00Z'
            }

            header = {'If-Match': etag}
            with freeze_time(datetime(2017, 1, 1)):
                r = self.api.patch("/blacklist/%s" % blacklist_id, data=patch,
                                   headers=header, token=self.get_root_token(),
                                   status_code=200)

            run_scheduled_tasks()

            # Only the creation email should be sent
            self.assertEqual(len(self.app.test_mails), 1)

            frozen_time.tick(delta=timedelta(days=1))

            run_scheduled_tasks()

            # Since the date was changed to the future, no email should be sent
            self.assertEqual(len(self.app.test_mails), 1)

            frozen_time.tick(delta=timedelta(days=1))

            run_scheduled_tasks()

            # Check mail
            mail = self.app.test_mails[1]
            self.assertEqual(mail['receivers'], 'bla@bla.bl')
            self.assertIn("Test1", mail['text'])
            self.assertIn("Test1", mail['html'])
            self.assertIn('removed', mail['text'])
            self.assertIn('removed', mail['html'])

    def test_scheduled_email_on_delete(self):
        """Test that a user receives only one an email if an entry is deleted"""
        with self.app.app_context(), freeze_time(
                "2017-01-01 00:00:00") as frozen_time:
            user_id = 24 * '0'
            blacklist_id = 24 * '1'

            # Create user and blacklist entry
            self.load_fixture({
                'users': [{'_id': user_id, 'email': "bla@bla.bl"}]
            })
            r = self.load_fixture({
                    'blacklist': [{
                        '_id': blacklist_id,
                        'user': user_id,
                        'reason': "Test1",
                        'end_time': "2017-01-02T00:00:00Z", }]
                })

            etag = r[0]['_etag']

            header = {'If-Match': etag}
            with freeze_time(datetime(2017, 1, 1)):
                r = self.api.delete("/blacklist/%s" % blacklist_id,
                                    headers=header, token=self.get_root_token(),
                                    status_code=204)

            run_scheduled_tasks()

            # Only the creation email should be sent
            self.assertEqual(len(self.app.test_mails), 2)

            frozen_time.tick(delta=timedelta(days=1))

            run_scheduled_tasks()

            # Since the entry was deleted no mail should be sent
            self.assertEqual(len(self.app.test_mails), 2)
