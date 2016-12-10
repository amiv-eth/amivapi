# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Tests for mailing list files."""

from os.path import isfile, join

from amivapi.tests.utils import WebTestNoAuth


class GroupModelTest(WebTestNoAuth):
    """Test creation and removal of mailing list files."""

    def _full_name(self, name):
        forward_path = self.app.config['FORWARD_DIR']
        return join(forward_path, '.forward+%s' % name)

    def assertForward(self, name, content):
        """Assert that the lines in the forward file are correct."""
        with open(self._full_name(name), 'r') as f:
            self.assertItemsEqual(content, f.read().split('\n'))

    def assertNoForward(self, name):
        """Assert the file doesnt exist."""
        self.assertFalse(isfile(self._full_name(name)))

    def test_new_group(self):
        """Test that a mailing list is created with the group."""
        receive = ['something', 'otherthing']
        forward = ['a@amiv.ch', 'b@amiv.ch']
        data = {'name': 'Test',
                'receive_from': receive,
                'forward_to': forward}
        self.api.post('/groups', data=data, status_code=201)

        for name in receive:
            self.assertForward(name, forward)

    def test_batch_insert(self):
        """Test creating several groups."""
        r1 = ['a-test']
        r2 = ['b.test_2']
        f1 = ['c@amiv.ch']
        f2 = ['d@amiv.ch']
        data = [{'name': 'first', 'receive_from': r1, 'forward_to': f1},
                {'name': 'second', 'receive_from': r2, 'forward_to': f2}]
        self.api.post('/groups', data=data, status_code=201)
        self.assertForward(r1[0], f1)
        self.assertForward(r2[0], f2)

    def _add_base_group(self):
        data = {'name': 'testgroup',
                'receive_from': ['r1', 'r2'],
                'forward_to': ['f1@amiv.ch', 'f2@amiv.ch']}
        r = self.api.post('/groups', data=data, status_code=201)
        return r.json

    def test_change_receive_from(self):
        """Test that new files are created and old ones removed."""
        r = self._add_base_group()
        self.api.patch('/groups/' + r['_id'], data={'receive_from': ['r1']},
                       headers={'If-Match': r['_etag']}, status_code=200)

        self.assertNoForward('r2')
        self.assertForward('r1', ['f1@amiv.ch', 'f2@amiv.ch'])

    def test_change_forward_to(self):
        r = self._add_base_group()
        self.api.patch('/groups/' + r['_id'],
                       data={'forward_to': ['new@amiv.ch']},
                       headers={'If-Match': r['_etag']}, status_code=200)

        self.assertForward('r1', ['new@amiv.ch'])
        self.assertForward('r2', ['new@amiv.ch'])

    def test_remove_group(self):
        r = self._add_base_group()
        self.api.delete('/groups/' + r['_id'],
                        headers={'If-Match': r['_etag']}, status_code=204)

        self.assertNoForward('r1')
        self.assertNoForward('r2')

    def _add_user_and_group(self):
        self.load_fixture({
            'users': [{'_id': 24 * '0',
                       'email': 'user@amiv.ch'},
                      {'_id': 24 * '1',
                       'email': 'other@amiv.ch'}],
            'groups': [{'_id': 24 * '2',
                        'receive_from': ['a'],
                        'forward_to': ['b@amiv.ch']}]
        })

    def test_add_and_remove_member(self):
        """Test adding a member creates the mailing lists again."""
        self._add_user_and_group()
        r = self.api.post('/groupmemberships',
                          data={'user': 24 * '0', 'group': 24 * '2'},
                          status_code=201).json

        self.assertForward('a', ['user@amiv.ch', 'b@amiv.ch'])

        self.api.delete('/groupmemberships/' + r['_id'],
                        headers={'If-Match': r['_etag']},
                        status_code=204)

        self.assertForward('a', ['b@amiv.ch'])

    def test_add_members_batch(self):
        self._add_user_and_group()
        data = [{'user': 24 * '0', 'group': 24 * '2'},
                {'user': 24 * '1', 'group': 24 * '2'}]
        self.api.post('/groupmemberships', data=data, status_code=201)

        self.assertForward('a',
                           ['user@amiv.ch', 'other@amiv.ch', 'b@amiv.ch'])

    def test_member_changes_email(self):
        """Test that the file gets renewed when a member changes his email."""
        self.load_fixture({
            'users': [{'_id': 24 * '0',
                       'email': 'user@amiv.ch'}],
            'groups': [{'_id': 24 * '1',
                        'receive_from': ['a']}],
            'groupmemberships': [{'user': 24 * '0', 'group': 24 * '1'}]
        })

        self.assertForward('a', ['user@amiv.ch'])

        # Patch user
        url = "/users/" + 24 * "0"
        etag = self.api.get(url, status_code=200).json['_etag']
        self.api.patch(url, headers={'If-Match': etag},
                       data={'email': "new@amiv.ch"}, status_code=200)

        self.assertForward('a', ['new@amiv.ch'])
