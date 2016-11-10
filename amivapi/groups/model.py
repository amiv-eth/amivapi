# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Group settings.

Contains models for groups and group mmeberships.
"""

from amivapi.auth import AmivTokenAuth
from amivapi.settings import EMAIL_REGEX

from bson import ObjectId

from flask import current_app


class GroupAuth(AmivTokenAuth):
    """Auth for groups."""

    def has_item_write_permission(self, user_id, item):
        """The group moderator is allowed to change things."""
        # item['moderator'] is Objectid, convert to str
        return item.get('moderator') and (user_id == str(item['moderator']))

    def create_user_lookup_filter(self, user_id):
        """Group lookup filter.

        Groups can be seen:
        - by the moderator and member
        - everyone, if self enrollment is allowed
        """
        # Find groups the user is in
        collection = current_app.data.driver.db['groupmemberships']
        memberships = collection.find({'user': ObjectId(user_id)},
                                      {'group': 1})
        groups = [item['group'] for item in memberships]

        return {'$or': [
            {'_id': {'$in': groups}},
            {'moderator': ObjectId(user_id)},
            {'allow_self_enrollment': True}
        ]}


class GroupMembershipAuth(AmivTokenAuth):
    """Auth for group memberships."""

    def has_resource_write_permission(self, user_id):
        """All user can signup for groups.

        The validator will check if the group in question is open for self
        enrollment to provide precise error messages.
        """
        return True

    def has_item_write_permission(self, user_id, item):
        """The group moderator and the member can change a signup."""
        if user_id == str(item['user']):
            # Own membership can be modified
            return True
        else:
            # Check if moderator
            # Note: Group must exist, otherwise membership would not exist
            #   Furthermore user_id can't be None so if there is no moderator
            #   we will correctly return False
            collection = current_app.data.driver.db['groups']
            group = collection.find_one({'_id': item['group']},
                                        {'moderator': 1})
            return user_id == str(group.get('moderator'))

    def create_user_lookup_filter(self, user_id):
        """Lookup for group members.

        Users can see memberships for groups:
        - they are members of
        - they moderate

        Possible improvement: Currently we need to find groupmemberships to
        create a filter for groupmemberships. Maybe this query can be done
        more elegant.
        """
        # Find groups the user moderates
        group_collection = current_app.data.driver.db['groups']
        groups = group_collection.find({'moderator': ObjectId(user_id)},
                                       {'_id': 1})
        moderated_groups = [group['_id'] for group in groups]

        # Find groups the user is in
        membership_collection = current_app.data.driver.db['groupmemberships']
        memberships = membership_collection.find({'user': ObjectId(user_id)},
                                                 {'group': 1})
        member_groups = [membership['group'] for membership in memberships]

        return {'$or': [
            {'group': {'$in': moderated_groups}},
            {'group': {'$in': member_groups}}
        ]}


groupdomain = {

    'groups': {
        'description': {
            'fields': {'allow_self_enrollment': 'If true, the group can be '
                       'seen by all users and they can subscribe themselves',
                       'has_zoidberg_share': 'If the group has a share in the '
                       'amiv storage',
                       'permissions': 'permissions the group grants. has to '
                       'be according to the jsonschema available at '
                       '/notyetavailable'},
            'general': "This resource describes the different teams in AMIV.A "
            "group can grant API permissions and can be reached with several "
            "addresses. To see the addresses of this group, see "
            "/groupaddressesTo see the members, have a look at "
            "'/groupmembers'. To see the addresses messages are forwarded to, "
            "see /groupforwards"},

        'resource_methods': ['POST', 'GET'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': GroupAuth,

        'schema': {
            'name': {
                'type': 'string',
                'maxlength': 100,
                'required': True,
                'unique': True,
                'empty': False
            },
            'moderator': {
                'type': 'objectid',
                'data_relation': {'resource': 'users'},
                'nullable': True
            },
            'receive_from': {
                'type': 'list',
                'unique_elements': True,
                'unique_elements_for_resource': True,
                'schema': {
                    'type': 'string',
                    'maxlength': 100,
                    'regex': '[a-z0-9_\.-]+'
                },
            },
            'forward_to': {
                'type': 'list',
                'unique_elements': True,
                'schema': {
                    'type': 'string',
                    'maxlength': 100,
                    'regex': EMAIL_REGEX
                }
            },
            'allow_self_enrollment': {
                'type': 'boolean',
                'default': False
            },
            'has_zoidberg_share': {
                'type': 'boolean',
                'default': False
            },
            'permissions': {
                'type': 'dict',
                'propertyschema': {'type': 'string',
                                   'api_resources': True},
                'valueschema': {'type': 'string',
                                'allowed': ['read', 'readwrite']},
                'nullable': True,
            }
        }
    },


    'groupmemberships': {
        'description': {'general': 'Assignment of registered users to groups.'},

        'resource_methods': ['POST', 'GET'],
        'item_methods': ['GET', 'DELETE'],  # No patching!

        'authentication': GroupMembershipAuth,

        'schema': {
            'group': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'groups',
                    'embeddable': True,
                    'cascade_delete': True  # Delete this if group is deleted
                },
                'required': True,
                'self_enrollment_required': True
            },
            'user': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                    'cascade_delete': True  # Delete this if user is deleted
                },
                'required': True,
                'only_self_or_moderator': True,
                'unique_combination': ['group']
            }
        }
    },
}
