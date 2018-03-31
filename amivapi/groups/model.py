# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Group settings.

Contains models for groups and group mmeberships.
"""
from bson import ObjectId
from flask import current_app

from amivapi.utils import get_id
from amivapi.auth import AmivTokenAuth
from amivapi.settings import EMAIL_REGEX


class GroupAuth(AmivTokenAuth):
    """Auth for groups."""

    def has_item_write_permission(self, user_id: str, item: dict) -> bool:
        """The group moderator is allowed to change things."""
        # Return true if a moderator exists and it is equal to the current user
        return item.get('moderator') and (
            user_id == str(get_id(item['moderator'])))

    def create_user_lookup_filter(self, user_id: str) -> dict:
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

    def has_resource_write_permission(self, user_id: str) -> bool:
        """All users can enroll in groups.

        Group-specific settings related to the question "who is allowed to
        enroll for this group?" are done in the validator.
        """
        return True

    def has_item_write_permission(self, user_id: str, item: dict) -> bool:
        """The group moderator and the member can change an enrollment."""
        if user_id == str(get_id(item['user'])):
            # Own membership can be modified
            return True
        else:
            # Check if moderator
            # Note: Group must exist, otherwise membership would not exist
            #   Furthermore user_id can't be None so if there is no moderator
            #   we will correctly return False
            collection = current_app.data.driver.db['groups']
            group = collection.find_one({'_id': get_id(item['group'])},
                                        {'moderator': 1})
            return user_id == str(group.get('moderator'))

    def create_user_lookup_filter(self, user_id: str) -> dict:
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
        'description': "This resource describes the different teams in AMIV. "
        "Being a member of a group can grant API permissions. Furthermore a "
        "group can have associated email addresses, which forward to all "
        "members of the group. Emails sent to the group can also be forwarded "
        "to other email addresses without an associated user. "
        "To see the members, have a look at '/groupmembers'.",

        'resource_methods': ['POST', 'GET'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': GroupAuth,

        # Additional lookup: Since group name is unique, you can use it as url
        'additional_lookup': {
            'url': 'regex("[\w]+")',
            'field': 'name'
        },

        'mongo_indexes': {
            'name': ([('name', 1)], {'background': True})
        },

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
                'nullable': True,
                'description': 'ID of a user which can add and remove members.'
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
                'description': 'Email addresses of this group. These addresses '
                'will forward to all group members and the additional addresses'
                ' specified by forward_to.'
            },
            'forward_to': {
                'type': 'list',
                'unique_elements': True,
                'schema': {
                    'type': 'string',
                    'maxlength': 100,
                    'regex': EMAIL_REGEX
                },
                'description': 'Additional addresses to which this group will '
                'forward emails.'
            },
            'allow_self_enrollment': {
                'type': 'boolean',
                'default': False,
                'description': 'If true, the group can be seen by all users and'
                ' they can subscribe themselves.'
            },
            'requires_storage': {
                'type': 'boolean',
                'default': False,
                'description': 'If the group has a share in the amiv storage.'
            },
            'permissions': {
                'type': 'dict',
                'propertyschema': {'type': 'string',
                                   'api_resources': True},
                'valueschema': {'type': 'string',
                                'allowed': ['read', 'readwrite']},
                'nullable': True,
                'description': 'permissions the group grants. The value is a '
                'json object with resources as properties and "read" or '
                '"readwrite" as a value.'
                # TODO: Make the schema available as a jsonschema
            }
        }
    },


    'groupmemberships': {
        'description': 'Assignment of registered users to groups.',

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
            },
            'expiry': {
                'type': 'datetime',
                'description': 'Time at which the person will automatically '
                'be removed from the group.'
            }
        }
    },
}
