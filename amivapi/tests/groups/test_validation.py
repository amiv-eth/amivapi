# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for custom validation rules for groups."""

from itertools import count

from amivapi.tests.utils import WebTest


class ValidationTest(WebTest):
    """Test creating, updating, deleting with different permissions."""

    def test_permission_schema(self):
        """Test the way permissions are added."""
        correct = [
            {'groups': 'read'},
            {'users': 'readwrite'}
        ]
        incorrect = [
            {'thisisnotaresource': 'read'},
            {'groups': 'thissettingiswrong'}
        ]
        token = self.get_root_token()
        c = count()
        for permissions in correct:
            data = {
                'name': "%s" % next(c),     # Just some random name
                'permissions': permissions
            }
            self.api.post("/groups", data=data,
                          token=token, status_code=201)

        for permissions in incorrect:
            data = {
                'name': "%s" % next(c),
                'permissions': permissions
            }
            self.api.post("/groups", data=data,
                          token=token, status_code=422)

    def test_no_double_membership(self):
        """A user can have only one membership per group."""
        user_id = 24 * '0'
        group_1_id = 24 * '1'
        group_2_id = 24 * '2'

        self.load_fixture({
            'users': [{'_id': user_id}],
            'groups': [{'_id': group_1_id}, {'_id': group_2_id}],
            'groupmemberships': [{'user': user_id, 'group': group_1_id}]
        })
        token = self.get_root_token()

        # Already member
        self.api.post("/groupmemberships", token=token,
                      data={'user': user_id, 'group': group_1_id},
                      status_code=422)

        # But can still be signed up for other groups
        self.api.post("/groupmemberships", token=token,
                      data={'user': user_id, 'group': group_2_id},
                      status_code=201)

    def enroll(self, data, token, code):
        """Test a enrollment for a group."""
        self.api.post("/groupmemberships",
                      data=data,
                      token=token, status_code=code)

    def test_allow_self_enrollment(self):
        """Assert allowing self enrollment works."""
        user_id = 24 * '0'
        allowed_id = 24 * '1'
        not_allowed_id = 24 * '2'
        self.load_fixture({
            'users': [{'_id': user_id}],
            'groups': [
                {'_id': allowed_id, 'allow_self_enrollment': True},
                {'_id': not_allowed_id, 'allow_self_enrollment': False}]
        })
        token = self.get_user_token(user_id)

        good_data = {'user': user_id, 'group': allowed_id},
        bad_data = {'user': user_id, 'group': not_allowed_id},

        self.enroll(good_data, token, 201)
        self.enroll(bad_data, token, 422)

    def test_enroll_by_mod(self):
        """Moderators can enroll others to their groups."""
        user_id = 24 * '0'
        mod_id = 24 * '1'
        mod_group_id = 24 * '2'
        other_group_id = 24 * '3'
        self.load_fixture({
            'users': [{'_id': user_id}, {'_id': mod_id}],
            'groups': [{'_id': mod_group_id,
                        'allow_self_enrollment': False,
                        'moderator': mod_id},
                       {'_id': other_group_id,
                        'allow_self_enrollment': False}]
        })

        data = {'user': user_id, 'group': mod_group_id}

        # User can't enroll, mod can
        self.enroll(data, self.get_user_token(user_id), 422)
        self.enroll(data, self.get_user_token(mod_id), 201)

        # Only for groups they moderate
        other_data = {'user': user_id, 'group': other_group_id}
        self.enroll(other_data, self.get_user_token(mod_id), 422)

    def test_enroll_by_admin(self):
        """Admins can enroll anyone."""
        user_id = 24 * '0'
        group_id = 24 * '1'
        self.load_fixture({
            'users': [{'_id': user_id}],
            'groups': [{'_id': group_id,
                        'allow_self_enrollment': False}]
        })

        data = {'user': user_id, 'group': group_id}

        # User can't enroll, mod can
        self.enroll(data, self.get_root_token(), 201)

    def test_only_self(self):
        """Test that only moderators can sign up users other them himself."""
        user_id = 24 * '0'
        other_user_id = 24 * '1'
        group_id = 24 * '2'

        self.load_fixture({
            'users': [{'_id': user_id}, {'_id': other_user_id}],
            'groups': [{'_id': group_id, 'allow_self_enrollment': True}]
        })

        token = self.get_user_token(user_id)
        good_data = {'user': user_id, 'group': group_id}
        bad_data = {'user': other_user_id, 'group': group_id}

        self.enroll(good_data, token, 201)
        print("now")
        self.enroll(bad_data, token, 422)
