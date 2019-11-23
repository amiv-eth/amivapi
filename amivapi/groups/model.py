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

    def has_item_write_permission(self, user_id, item):
        """The group moderator is allowed to change things."""
        # Return true if a moderator exists and it is equal to the current user
        return item.get('moderator') and (
            user_id == str(get_id(item['moderator'])))

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
        """All users can enroll in groups.

        Group-specific settings related to the question "who is allowed to
        enroll for this group?" are done in the validator.
        """
        return True

    def has_item_write_permission(self, user_id, item):
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


description_group = ("""
A group is a team within the organization, e.g. the "Vorstand" (board) or
"Kulturteam" (event team).

Groups act as mailing lists, and can grant API permissions to all
[Group Members][1].

<br />

## Moderators and Members

There are two kinds of groups,

- those that allow self enrollment of users,
- and those that do not.

A **user** can only see groups he or she is already a member of and groups
that allow self enrollment. All other groups are hidden.
Furthermore, it is only possible to become a member of a group if self
enrollment is enabled.
Finally, users cannot modify groups in any way.

An **admin** can see all groups, can add any user to any group (this is the
only way to add members to groups that do not allow self enrollment), and can
also update groups.

A group has a **moderator**, specified by the `moderator` field. The moderator
has the same permissions as an admin, but only for the moderated group.
An exception to this are group permissions (see below): These can only be
changed by admins.

<br />

## Mailing Lists

Groups act as mailing lists, so that all members of a group can be reached
quickly.

A group mailing list can receive mail from multiple addresses specified by the
`receive_from` field. This can only be the *local part* of the address
(e.g. `john` instead of `john@smith.com`), as the mail server address cannot
be influenced by the API.

All emails sent to the mailing list are forwarded to

- all members of the group,
- and additional email addresses specified in the `forward_to` field

### Example

| Group          |                               |
|----------------|-------------------------------|
| Members        | Pablo (email: `pablo@api.ch`) |
| `receive_from` | `["test"]`                    |
| `forward_to`   | `["backup@external.ch"]`      |

If the mailserver is `api.ch`, the group will receive all mails from
`test@api.ch` and forward them to `backup@external.ch` and `pablo@api.ch`.


<br />

## Permissions

Groups are often tied to certain tasks, e.g. the event team needs to be able to
manage events. Therefore it is possible to add **permissions** to a group, i.e.
grant all group members admin rights for certain API functionality.

There are two kinds of permissions, `read` and `readwrite` (see more [here][2])
and they are granted *per resource*.

In the `permissions` field, you can send an object with the resources as keys
and the respective permissions as values, e.g.

```
{
    "users": "read",
    "sessions": "readwrite"
}
```

(this would grant every member of the group rights to see all users and see
and modify/delete all sessions).

> **IMPORTANT: The most powerful permission**
>
> As group admins are able to modify groups and thereby modify the group
> permissions, they effectively have access to all permissions and are the
> 'true' admins in the API.
>
> Along the same lines, you have to be careful with permissions for
> [API keys][3], as this permission allows to create API keys with arbitrary
> permissions which can be used for subsequent requests.
>
> As a result, **`readwrite` permissions for groups and API keys should only
> be assigned with great care**!

[1]: #tag/Groupmembership
[2]: #section/Authentication-and-Authorization/Authorization
[3]: #tag/Apikey
""")


description_groupmembership = ("""
A membership to a [group][1].

Group members are granted permissions by the group and can be reached via
mails sent to the group. Check out the group description for more info.

[1]: #tag/Group
""")


groupdomain = {

    'groups': {
        'description': description_group,

        'resource_methods': ['POST', 'GET'],
        'item_methods': ['GET', 'PATCH', 'DELETE'],

        'authentication': GroupAuth,

        # Additional lookup: Since group name is unique, you can use it as url
        'additional_lookup': {
            'url': 'string',
            'field': 'name',
        },

        'mongo_indexes': {
            'name': ([('name', 1)], {'background': True})
        },

        'schema': {
            'name': {
                'description': 'The unique name identifying the group.',
                'example': 'Kulturteam',

                'type': 'string',
                'maxlength': 100,
                'required': True,
                'unique': True,
                'empty': False,
                'no_html': True,
            },
            'moderator': {
                'description': '`_id` of a user which will be the group '
                               'moderator, who can modify the group and its '
                               'members.',
                'example': 'ed1ac3fa99034762f7b55e5a',

                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                },
                'nullable': True,
                'default': None,
            },
            'receive_from': {
                'description': 'Email addresses from which the group will '
                               'receive mails. Must only contain a local '
                               'address (everything before the @), as the '
                               'rest is determined by the (external) mail '
                               'server.',
                'example': ['kulturteam', 'events', 'kultur'],

                'type': 'list',
                'unique_elements': True,
                'unique_elements_for_resource': True,
                'schema': {
                    'type': 'string',
                    'maxlength': 100,
                    'regex': r'[a-z0-9_\.-]+'
                },
                'nullable': True,
                'default': None,
            },
            'forward_to': {
                'description': 'Additional addresses to which this group will '
                               'forward emails.',
                'example': ['external@backup.ch'],

                'type': 'list',
                'unique_elements': True,
                'schema': {
                    'type': 'string',
                    'maxlength': 100,
                    'regex': EMAIL_REGEX
                },
                'nullable': True,
                'default': None,
            },
            'allow_self_enrollment': {
                'description': 'If true, the group can be seen by all users and'
                               ' they can subscribe themselves.',
                'example': True,

                'type': 'boolean',
                'default': False,
            },
            'requires_storage': {
                'type': 'boolean',
                'default': False,
                'description': 'If the group requires storage space. This is '
                               'only an indicator for other tools, the API '
                               'does not provide the space itself.',
            },
            'permissions': {
                'description': 'The permissions the group grants. The value is '
                               'an object with resources as keys and the '
                               'permissions as a values.',
                'example': {
                    'users': 'read',
                    'sessions': 'readwrite',
                },

                'type': 'dict',
                'keysrules': {'type': 'string',
                              'api_resources': True},
                'valuesrules': {'type': 'string',
                                'allowed': ['read', 'readwrite']},
                'nullable': True,
                'default': None,
                'admin_only': True,
            }
        }
    },


    'groupmemberships': {
        'resource_title': 'Group Memberships',
        'item_title': 'Group Membership',

        'description': description_groupmembership,

        'resource_methods': ['POST', 'GET'],
        'item_methods': ['GET', 'DELETE'],  # No patching!

        'authentication': GroupMembershipAuth,

        'schema': {
            'group': {
                'example': 'e0fb1d077ff6ca3c9dd731c4',

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
                'example': '679ff66720812cdc2da4fb4a',

                'type': 'objectid',
                'data_relation': {
                    'resource': 'users',
                    'embeddable': True,
                    'cascade_delete': True  # Delete memberships with user
                },
                'required': True,
                'only_self_or_moderator': True,
                'unique_combination': ['group']
            },
            'expiry': {
                'type': 'datetime',
                'description': 'Time at which the user is automatically '
                               'removed from the group. Can be set to '
                               'Null for no expiry.',
                'example': '2018-11-03T16:01:00Z',
                'nullable': True,
                'default': None,
            }
        }
    },
}
