# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for purchases module"""

from datetime import datetime, timedelta

from amivapi.tests import utils
from amivapi.settings import DATE_FORMAT


class BeveragesTest(utils.WebTestNoAuth):
    """Test basic functionality of beverages"""

    def test_can_have_drink(self):
        """Usecase: Vending machine wants to determine, if the user already
        had his daily drink"""

        user = self.new_object('users')

        # Should return no beverages, if none have been done
        p = self.api.get(
            '/beverages?where={"user": "%s", "product":"beer", '
            '"timestamp": {"$gte": "%s"}}'
            % (str(user['_id']), datetime.utcnow().strftime(DATE_FORMAT)),
            status_code=200).json['_items']
        self.assertEqual(len(p), 0)

        # Next test with a transaction 2 days ago
        self.new_object('beverages', user=user['_id'], product='beer',
                        timestamp=datetime.utcnow() - timedelta(days=2))

        p = self.api.get(
            '/beverages?where={"user": "%s", "product":"beer", '
            '"timestamp": {"$gte": "%s"}}'
            % (str(user['_id']), datetime.utcnow().strftime(DATE_FORMAT)),
            status_code=200).json['_items']
        self.assertEqual(len(p), 0)

        # Now we add a beverage and ask again
        self.new_object('beverages', user=user['_id'], product='beer',
                        timestamp=datetime.utcnow())

        time = (datetime.utcnow() - timedelta(hours=1)).strftime(DATE_FORMAT)
        p = self.api.get(
            '/beverages?where={"user": "%s", "product":"beer", '
            '"timestamp": {"$gte": "%s"}}'
            % (str(user['_id']), time),
            status_code=200).json['_items']
        self.assertEqual(len(p), 1)

    def test_add_beverage(self):
        """Usecase: Vending machine dispensed an item and wants to register that
        """

        user = self.new_object('users')

        p = self.api.get("/beverages", status_code=200).json['_items']
        self.assertTrue(len(p) == 0)

        post_data = {
            'user': str(user['_id']),
            'product': 'beer',
            'timestamp': datetime.utcnow().strftime(DATE_FORMAT)
        }

        self.api.post("/beverages", data=post_data, status_code=201)


class BeveragesAuthTest(utils.WebTest):
    """Test correct permissions for beverages"""

    def test_beverages_privacy(self):
        """Test that users can only see their own beverages"""
        user1 = self.new_object('users')
        user2 = self.new_object('users')
        u1_token = self.get_user_token(str(user1['_id']))
        u2_token = self.get_user_token(str(user2['_id']))

        b1 = self.new_object('beverages', user=user1['_id'])
        b2 = self.new_object('beverages', user=user2['_id'])

        u1_beverages = self.api.get(
            "/beverages", token=u1_token, status_code=200).json['_items']

        self.assertEqual(len(u1_beverages), 1)
        self.assertEqual(u1_beverages[0]['_id'], str(b1['_id']))

        u2_beverages = self.api.get(
            "/beverages", token=u2_token, status_code=200).json['_items']

        self.assertEqual(len(u2_beverages), 1)
        self.assertEqual(u2_beverages[0]['_id'], str(b2['_id']))
