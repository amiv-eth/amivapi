# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for purchases module"""

from datetime import datetime, timedelta

from amivapi.tests import utils
from amivapi.settings import DATE_FORMAT


class PurchaseTest(utils.WebTestNoAuth):
    """Test basic functionality of purchases"""

    def test_can_have_drink(self):
        """Usecase: Vending machine wants to determine, if the user already
        had his daily drink"""

        user = self.new_user()

        # Should return no purchases, if none have been done
        p = self.api.get(
                '/purchases?where={"user": "%s", "product":"beer", '
                '"timestamp": {"$gte": "%s"}}'
                % (str(user['_id']), datetime.utcnow().strftime(DATE_FORMAT)),
                status_code=200).json['_items']
        self.assertEqual(len(p), 0)

        # Next test with a transaction 2 days ago
        self.new_purchase(user=user['_id'], product='beer',
                          timestamp=datetime.utcnow() - timedelta(days=2))

        p = self.api.get(
                '/purchases?where={"user": "%s", "product":"beer", '
                '"timestamp": {"$gte": "%s"}}'
                % (str(user['_id']), datetime.utcnow().strftime(DATE_FORMAT)),
                status_code=200).json['_items']
        self.assertEqual(len(p), 0)

        # Now we add a purchase and ask again
        self.new_purchase(user=user['_id'], product='beer',
                          timestamp=datetime.utcnow())

        time = (datetime.utcnow() - timedelta(hours=1)).strftime(DATE_FORMAT)
        p = self.api.get(
                '/purchases?where={"user": "%s", "product":"beer", '
                '"timestamp": {"$gte": "%s"}}'
                % (str(user['_id']), time),
                status_code=200).json['_items']
        self.assertEqual(len(p), 1)

    def test_add_purchase(self):
        """Usecase: Vending machine dispensed an item and wants to register that
        """

        user = self.new_user()

        p = self.api.get("/purchases", status_code=200).json['_items']
        self.assertTrue(len(p) == 0)

        post_data = {
            'user': str(user['_id']),
            'product': 'beer',
            'timestamp': datetime.utcnow().strftime(DATE_FORMAT)
        }

        self.api.post("/purchases", data=post_data, status_code=201)


class PurchaseAuthTest(utils.WebTest):
    """Test correct permissions for purchases"""

    def test_purchase_privacy(self):
        """Test that users can only see their own purchases"""
        user1 = self.new_user()
        user2 = self.new_user()
        u1_token = self.get_user_token(str(user1['_id']))
        u2_token = self.get_user_token(str(user2['_id']))

        p1 = self.new_purchase(user=user1['_id'])
        p2 = self.new_purchase(user=user2['_id'])

        u1_purchases = self.api.get(
            "/purchases", token=u1_token, status_code=200).json['_items']

        self.assertEqual(len(u1_purchases), 1)
        self.assertEqual(u1_purchases[0]['_id'], str(p1['_id']))

        u2_purchases = self.api.get(
            "/purchases", token=u2_token, status_code=200).json['_items']

        self.assertEqual(len(u2_purchases), 1)
        self.assertEqual(u2_purchases[0]['_id'], str(p2['_id']))
