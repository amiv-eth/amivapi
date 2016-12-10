# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for group model including auth."""

from amivapi.tests.utils import WebTest


class GroupModelTest(WebTest):
    """Test creating, updating, deleting with different permissions."""

    def test_nothing_public(self):
        """Test configuration: Make sure nothing is public."""
        self.load_fixture({'groups': [{'_id': 24 * '0'}]})
        res_url = "/groups"
        item_url = "/groups/%s" % (24 * "0")
        self.api.get(res_url, data={}, status_code=401)
        self.api.post(res_url, data={}, status_code=401)
        self.api.get(item_url, data={}, status_code=401)
        self.api.patch(item_url, data={}, status_code=401)
        self.api.delete(item_url, data={}, status_code=401)

    def test_users_cant_create(self):
        """Normal users can't create anything."""
        self.load_fixture({'users': [{'_id': 24 * "0"}]})  # Create a user
        self.api.post("/groups",
                      token=self.get_user_token(24 * "0"), data={},
                      status_code=403)

    def test_create(self):
        """Test to create group with all fields."""
        self.load_fixture({'users': [{'_id': 24 * "0"}]})  # Create a user
        data = {
            'name': 'testgroup',
            'moderator': 24 * '0',
            'receive_from': ['test1@amiv.ch', 'test2@amiv.ch'],
            'forward_to': ['test3@amiv.ch', 'test4@amiv.ch'],
        }
        self.api.post("/groups", data=data, token=self.get_root_token(),
                      status_code=201)

    def test_additional_lookup(self):
        """Test that you can use groupname for lookup."""
        self.new_object("groups", name="testname")

        self.api.get("/groups/testname", token=self.get_root_token(),
                     status_code=200)

    def test_lookup_filter(self):
        """Test lookup.

        A group can be seend by
        - moderator
        - members
        - everyone, if self enrollment is allowed
        """
        user_id = 24 * '0'
        hidden_group_id = 24 * '1'
        member_group_id = 24 * '2'
        moderator_group_id = 24 * '3'
        enrollment_group_id = 24 * '4'

        self.load_fixture({
            # Create user
            'users': [{'_id': user_id}],
            # Set up different groups
            'groups': [
                {'_id': hidden_group_id},
                {'_id': member_group_id},
                {'_id': moderator_group_id, 'moderator': user_id},
                {'_id': enrollment_group_id, 'allow_self_enrollment': True}
            ],
            # Add user to one group
            'groupmemberships': [{'group': member_group_id, 'user': user_id}]
        })

        token = self.get_user_token(user_id)

        # Resource Lookup
        r = self.api.get("/groups", token=token, status_code=200).json
        group_ids = [item['_id'] for item in r['_items']]

        self.assertNotIn(hidden_group_id, group_ids)
        for gid in (member_group_id, moderator_group_id, enrollment_group_id):
            self.assertIn(gid, group_ids)

        # Item lookups
        self.api.get("/groups/%s" % hidden_group_id, token=token,
                     status_code=404)
        for gid in (member_group_id, moderator_group_id, enrollment_group_id):
            self.api.get("/groups/%s" % gid, token=token, status_code=200)

    def test_item_write(self):
        """Member cant patch and delete, moderator can."""
        user_id = 24 * '0'
        mod_id = 24 * '1'
        group_id = 24 * '2'

        self.load_fixture({'users': [{'_id': user_id}, {'_id': mod_id}]})
        group = self.load_fixture({
            'groups': [{'_id': group_id, 'moderator': mod_id}]
        })
        self.load_fixture({
            'groupmemberships': [{'user': user_id, 'group': group_id}]
        })
        etag = group[0]['_etag']
        user_token = self.get_user_token(user_id)
        mod_token = self.get_user_token(mod_id)

        patch = {'has_zoidberg_share': True}
        header = {'If-Match': etag}

        self.api.patch("/groups/%s" % group_id, data=patch, headers=header,
                       token=user_token, status_code=403)

        r = self.api.patch("/groups/%s" % group_id,
                           data=patch, headers=header,
                           token=mod_token, status_code=200)

        header['If-Match'] = r.json['_etag']
        self.api.delete("/groups/%s" % group_id, headers=header,
                        token=user_token, status_code=403)
        self.api.delete("/groups/%s" % group_id, headers=header,
                        token=mod_token, status_code=204)


class GroupMembershipModelTest(WebTest):
    """Test Groupmemberships."""

    item_url = "/groupmemberships/%s"

    def assertVisible(self, membership_id, token):
        """Assert a membership is visible."""
        self.api.get(self.item_url % membership_id,
                     token=token, status_code=200)
        resource_response = self.api.get("/groupmemberships",
                                         token=token, status_code=200).json
        visible_ids = [item['_id'] for item in resource_response['_items']]
        self.assertIn(membership_id, visible_ids)

    def assertNotVisible(self, membership_id, token):
        """Assert a membership is visible."""
        self.api.get(self.item_url % membership_id,
                     token=token, status_code=404)
        resource_response = self.api.get("/groupmemberships",
                                         token=token, status_code=200).json
        visible_ids = [item['_id'] for item in resource_response['_items']]
        self.assertNotIn(membership_id, visible_ids)

    def assertDelete(self, membership_id, token):
        """Assert a membership can be deleted."""
        # Get etag
        etag = self.api.get(self.item_url % membership_id, token=token,
                            status_code=200).json['_etag']
        self.api.delete(self.item_url % membership_id, token=token,
                        headers={'If-Match': etag}, status_code=204)

    def assertNoDelete(self, membership_id, token):
        """Assert a (visible) membership can't be deleted.

        If the membership can not be seen, delete will not be possible any way.
        """
        # Get etag
        etag = self.api.get(self.item_url % membership_id,
                            token=token, status_code=200).json['_etag']
        self.api.delete(self.item_url % membership_id, token=token,
                        headers={'If-Match': etag}, status_code=403)

    def test_no_patch(self):
        """No patching."""
        self.load_fixture({
            'groups': [{}],
            'users': [{}],
            'groupmemberships': [{'_id': 24 * '0'}]})
        self.api.patch(self.item_url % (24 * '0'), data={},
                       token=self.get_root_token(), status_code=405)

    def test_public_cant_see_or_modify(self):
        """A public user cant do anything."""
        self.load_fixture({
            'groups': [{}],
            'users': [{}],
            'groupmemberships': [{'_id': 24 * '0'}]})
        res_url = "/groupmemberships"
        self.item_url = self.item_url % (24 * "0")
        self.api.get(res_url, data={}, status_code=401)
        self.api.post(res_url, data={}, status_code=401)
        self.api.get(self.item_url, data={}, status_code=401)
        self.api.delete(self.item_url, data={}, status_code=401)

    def test_user_can_see_all_group_members(self):
        """A Members of a group can see all other members."""
        user_id = 24 * '0'
        other_id = 24 * '1'
        user_group_membership_id_1 = 24 * '2'
        user_group_membership_id_2 = 24 * '3'
        other_group_membership_id = 24 * '4'
        self.load_fixture({
            'users': [{'_id': user_id},
                      {'_id': other_id}],
            'groups': [{'_id': user_id},
                       {'_id': other_id}],
            'groupmemberships': [
                {'_id': user_group_membership_id_1,
                 'user': user_id, 'group': user_id},
                {'_id': user_group_membership_id_2,
                 'user': other_id, 'group': user_id},
                {'_id': other_group_membership_id,
                 'user': other_id, 'group': other_id}
            ]
        })
        token = self.get_user_token(user_id)
        # Group with id user_id is visible to the user
        self.assertVisible(user_group_membership_id_1, token)
        self.assertVisible(user_group_membership_id_2, token)
        # the other group not because the user is not a member
        self.assertNotVisible(other_group_membership_id, token)

    def test_user_can_delete_only_own_memberships(self):
        """A user can only modify his own memberships."""
        user_id = 24 * '0'
        other_id = 24 * '1'
        self.load_fixture({
            'users': [{'_id': user_id},
                      {'_id': other_id}],
            'groups': [{}],
            'groupmemberships': [{'_id': user_id, 'user': user_id},
                                 {'_id': other_id, 'user': other_id}]
        })
        token = self.get_user_token(user_id)
        self.assertNoDelete(other_id, token)
        self.assertDelete(user_id, token)

    def test_mod_can_see_and_delete_group_memberships(self):
        """A moderator can modify all memberships of moderated group."""
        mod_id = 24 * '0'
        other_id = 24 * '1'
        self.load_fixture({
            'users': [{'_id': mod_id}, {'_id': other_id}],
            'groups': [{'_id': mod_id, 'moderator': mod_id},
                       {'_id': other_id}],
            'groupmemberships': [
                {'_id': mod_id, 'user': other_id, 'group': mod_id},
                {'_id': other_id, 'user': other_id, 'group': other_id}]
        })
        token = self.get_user_token(mod_id)

        # Can't see membership of other groups (-> can't modify either)
        self.assertNotVisible(other_id, token)

        self.assertVisible(mod_id, token)
        self.assertDelete(mod_id, token)

    def assertCascade(self, res):
        """Assert that user or group delete cascades.

        Args:
            res (str): Can be either 'users' or 'groups'
        """
        _id = 24 * '0'
        token = self.get_root_token()

        self.load_fixture({
            'users': [{'_id': _id}],
            'groups': [{'_id': _id}],
            'groupmemberships': [{'_id': _id, 'user': _id, 'group': _id}]
        })

        # Membership exists
        self.api.get(self.item_url % _id, token=token, status_code=200)

        # Get etag and delete user/group
        etag = self.api.get("/%s/%s" % (res, _id), token=token,
                            status_code=200).json['_etag']
        self.api.delete("/%s/%s" % (res, _id), token=token,
                        headers={'If-Match': etag}, status_code=204)

        # Membership gone
        self.api.get(self.item_url % _id, token=token, status_code=404)

    def test_cascade_user_delete(self):
        """Deleting user removes the memberships."""
        self.assertCascade("users")

    def test_cascade_group_delete(self):
        """Deleting group removes the memberships."""
        self.assertCascade("groups")
