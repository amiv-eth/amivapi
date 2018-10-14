# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Test that people are correctly added and removed from the waiting list"""

from amivapi.tests.utils import WebTestNoAuth


class EventsignupQueueTest(WebTestNoAuth):
    def test_manual_queue_no_one_accepted(self):
        """Test that no one gets accepted for a manual picking event."""
        event = self.new_object('events', spots=100,
                                selection_strategy='manual')

        user = self.new_object('users')

        response = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        self.assertFalse(response['accepted'])

    def test_fcfs_users_get_auto_accepted(self):
        """Test that with fcfs the users get automatically accepted on signup
        and also when a space becomes available"""
        event = self.new_object('events', spots=1,
                                selection_strategy='fcfs')

        user1 = self.new_object('users')
        user2 = self.new_object('users')

        user1_signup = self.api.post('/eventsignups', data={
            'user': str(user1['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        self.assertTrue(user1_signup['accepted'])

        user2_signup = self.api.post('/eventsignups', data={
            'user': str(user2['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        self.assertFalse(user2_signup['accepted'])

        # delete the accepted signup
        self.api.delete('/eventsignups/%s' % user1_signup['_id'],
                        headers={'If-Match': user1_signup['_etag']},
                        status_code=204)

        # Check that the other user got accepted
        user2_signup = self.api.get('/eventsignups/%s' % user2_signup['_id'],
                                    status_code=200).json
        self.assertTrue(user2_signup['accepted'])

    def test_fcfs_users_get_auto_accepted_unlimited_spots(self):
        """Test that with fcfs the users get automatically accepted on signup
        for events with unlimited spaces"""
        event = self.new_object('events', spots=0,
                                selection_strategy='fcfs')

        user = self.new_object('users')

        signup = self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        self.assertTrue(signup['accepted'])

    def test_removing_from_waitinglist_does_nothing(self):
        """Test that removing someone from the waitinglist, who did not have
        space, does not crash.

        The reason for this test is
        1. Test coverage, as that is a special case in some hooks.
        2. Making sure nothing weird happens, like API crashes for those code
        paths."""
        event = self.new_object('events', spots=1, selection_strategy='fcfs')
        user = self.new_object('users')
        user2 = self.new_object('users')

        self.api.post('/eventsignups', data={
            'user': str(user['_id']),
            'event': str(event['_id'])
        }, status_code=201)

        signup2 = self.api.post('/eventsignups', data={
            'user': str(user2['_id']),
            'event': str(event['_id'])
        }, status_code=201).json

        self.api.delete('/eventsignups/%s' % signup2['_id'],
                        headers={'If-Match': signup2['_etag']},
                        status_code=204)
