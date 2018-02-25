# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Tests for mailing list files.

To run integration tests for remote files, set the following environment
variables:

REMOTE_MAILING_LIST_ADDRESS: user@remote.host
REMOTE_MAILING_LIST_KEYFILE: path to your keyfile, optional
REMOTE_MAILING_LIST_DIR: storage path on remote server, default is './',
                         `/tmp/apitest` or similar might be a good idea

"""

import pytest

from os import getenv
from os.path import isfile, join
from shutil import rmtree
from tempfile import mkdtemp

from mock import patch, call

from amivapi.tests.utils import WebTestNoAuth

from amivapi.groups.mailing_lists import (
    make_files, remove_files, ssh_command, ssh_create, ssh_remove)


class MailingListTest(WebTestNoAuth):
    """Test creation and removal of mailing list files."""

    def setUp(self):
        """Create a temporary directory for mailing lists."""
        super(MailingListTest, self).setUp()
        base_dir = mkdtemp(prefix='amivapi_test')
        self.app.config['MAILING_LIST_DIR'] = join(base_dir, 'lists')

    def tearDown(self):
        """Remove temporary directory."""
        directory = self.app.config['MAILING_LIST_DIR']
        rmtree(directory, ignore_errors=True)
        super(MailingListTest, self).tearDown()

    def _full_name(self, name):
        list_path = self.app.config['MAILING_LIST_DIR']
        list_prefix = self.app.config['MAILING_LIST_FILE_PREFIX']
        return join(list_path, list_prefix + name)

    def assertFileContent(self, name, content):
        """Assert that the lines in the mailing list file are correct."""
        with open(self._full_name(name), 'r') as file:
            self.assertItemsEqual(content, file.read().split('\n'))

    def assertNoFile(self, name):
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
            self.assertFileContent(name, forward)

    def test_batch_insert(self):
        """Test creating several groups."""
        r1 = ['a-test']
        r2 = ['b.test_2']
        f1 = ['c@amiv.ch']
        f2 = ['d@amiv.ch']
        data = [{'name': 'first', 'receive_from': r1, 'forward_to': f1},
                {'name': 'second', 'receive_from': r2, 'forward_to': f2}]
        self.api.post('/groups', data=data, status_code=201)
        self.assertFileContent(r1[0], f1)
        self.assertFileContent(r2[0], f2)

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

        self.assertNoFile('r2')
        self.assertFileContent('r1', ['f1@amiv.ch', 'f2@amiv.ch'])

    def test_change_forward_to(self):
        r = self._add_base_group()
        self.api.patch('/groups/' + r['_id'],
                       data={'forward_to': ['new@amiv.ch']},
                       headers={'If-Match': r['_etag']}, status_code=200)

        self.assertFileContent('r1', ['new@amiv.ch'])
        self.assertFileContent('r2', ['new@amiv.ch'])

    def test_remove_group(self):
        r = self._add_base_group()
        self.api.delete('/groups/' + r['_id'],
                        headers={'If-Match': r['_etag']}, status_code=204)

        self.assertNoFile('r1')
        self.assertNoFile('r2')

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

        self.assertFileContent('a', ['user@amiv.ch', 'b@amiv.ch'])

        self.api.delete('/groupmemberships/' + r['_id'],
                        headers={'If-Match': r['_etag']},
                        status_code=204)

        self.assertFileContent('a', ['b@amiv.ch'])

    def test_add_members_batch(self):
        self._add_user_and_group()
        data = [{'user': 24 * '0', 'group': 24 * '2'},
                {'user': 24 * '1', 'group': 24 * '2'}]
        self.api.post('/groupmemberships', data=data, status_code=201)

        self.assertFileContent('a',
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

        self.assertFileContent('a', ['user@amiv.ch'])

        # Patch user
        url = "/users/" + 24 * "0"
        etag = self.api.get(url, status_code=200).json['_etag']
        self.api.patch(url, headers={'If-Match': etag},
                       data={'email': "new@amiv.ch"}, status_code=200)

        self.assertFileContent('a', ['new@amiv.ch'])


class RemoteMailingListTest(WebTestNoAuth):
    """Test creation and removal of remote mailing list files via ssh.

    The local mailing list tests already ensure that the functions to create
    and remove files are working properly, these tests only make sure that
    the ssh functions are called if required:

    Ssh should be the case if the REMOTE_MAILING_LIST_ADDRESS is set.
    The ssh calls are mocked (separate integration tests for actual conn.)
    """

    def setUp(self):
        """Set config key and mock ssh call."""
        super(RemoteMailingListTest, self).setUp()
        self.app.config['REMOTE_MAILING_LIST_ADDRESS'] = 'not none!'

    def test_remote_create_called(self):
        """Test that creating the file over ssh is attempted."""
        with patch('amivapi.groups.mailing_lists.ssh_create') as create:
            group_id = 24 * '0'
            receive_from = ['a', 'b']
            self.load_fixture({
                'groups': [{'_id': group_id, 'receive_from': receive_from}]
            })
            with self.app.app_context():
                make_files(group_id)
                # Both times there will be no content
                create.assert_has_calls(
                    [call(address, '') for address in receive_from],
                    any_order=True
                )

    def test_remote_remove_called(self):
        """Test that removing the file over ssh is attempted."""
        addresses = ['a', 'b']
        with patch('amivapi.groups.mailing_lists.ssh_remove') as remove:
            with self.app.app_context():
                remove_files(addresses)
                remove.assert_has_calls(
                    [call(address) for address in addresses],
                    any_order=True
                )


def skip_without_address(func):
    """Decorator to mark tests to be skipped if envvar is not set."""
    if getenv('REMOTE_MAILING_LIST_ADDRESS'):
        return func
    else:
        return pytest.mark.skip(reason="Test")(func)


class SSHIntegrationTest(WebTestNoAuth):
    """Test the actual ssh connection.

    You need to set environment variables to run these tests:

    REMOTE_MAILING_LIST_ADDRESS: user@remote.host
    REMOTE_MAILING_LIST_KEYFILE: path to your keyfile, optional
    REMOTE_MAILING_LIST_DIR: storage path on remote server, default is './'

    py.test will inform you if the tests are skipped.
    """
    def setUp(self):
        """Set config keys from environment variables."""
        super(SSHIntegrationTest, self).setUp()
        for var in ['ADDRESS', 'KEYFILE', 'DIR']:
            full_var = 'REMOTE_MAILING_LIST_%s' % var
            self.app.config[full_var] = getenv(full_var)

    def get_remote_path(self, filename):
        return join(self.app.config['REMOTE_MAILING_LIST_DIR'],
                    self.app.config['MAILING_LIST_FILE_PREFIX'] + filename)

    def assert_remote_content(self, filename, content):
        """Use ssh to verify remote file content."""
        self.assertEqual(
             content, ssh_command('cat %s' % self.get_remote_path(filename)))

    def assert_remote_does_not_exist(self, filename):
        """Use ssh to verify remote file does not exist."""
        path = self.get_remote_path(filename)
        # ls <filename> returns the filename (if it exists). Error otherwise.
        with self.assertRaises(RuntimeError):
            ssh_command('ls %s' % path)

    @skip_without_address
    def test_create_and_remove(self):
        """Test that a file can be created and removed.

        (Both in same test to clean up remote server)
        """
        with self.app.app_context():
            filename = 'test.txt'
            content = 'test@amiv.ch\ntest2@amiv.ch\n'
            self.assert_remote_does_not_exist(filename)

            ssh_create(filename, content)
            self.assert_remote_content(filename, content)

            ssh_remove(filename)
            self.assert_remote_does_not_exist(filename)

    @skip_without_address
    def test_remove_does_not_raise(self):
        """Remove will not raise an exception for missing files."""
        with self.app.app_context():
            filename = 'ThisDoesNotExistsIHope.txt'
            self.assert_remote_does_not_exist(filename)
            ssh_remove(filename)  # No Exception should crash the test
