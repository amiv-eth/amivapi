# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Api group resource settings.

Contains groups, groupmemberships, groupaddresses and forwards.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Unicode,
    Integer,
    Boolean)
from sqlalchemy.orm import relationship

from amivapi.utils import (
    EMAIL_REGEX,
    make_domain,
    Base,
    JSONText
)
from amivapi.users import User


class Group(Base):
    """Group model."""

    __description__ = {
        'general': "This resource describes the different teams in AMIV."
        "A group can grant API permissions and can be reached with several "
        "addresses. To see the addresses of this group, see /groupaddresses"
        "To see the members, have a look at '/groupmembers'. "
        "To see the addresses messages are forwarded to, see /groupforwards",
        'fields': {
            'allow_self_enrollment': "If true, the group can be seen by all "
            "users and they can subscribe themselves",
            'has_zoidberg_share': "Wether the group has a share in the amiv "
            "storage",
            "permissions": "permissions the group grants. has to be according "
            "to the jsonschema available at /notyetavailable"  # TODO!
        }}
    __expose__ = True
    __projected_fields__ = ['members', 'addresses', 'forwards']
    __embedded_fields__ = ['members', 'addresses', 'forwards']

    __owner__ = ['moderator_id', 'members.user_id']
    __owner_methods__ = ['GET']  # Only admins can modify the group itself!

    __registered_methods__ = ['GET']  # All users can check for open groups

    name = Column(Unicode(100), unique=True, nullable=False)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allow_self_enrollment = Column(Boolean, default=False, nullable=False)

    has_zoidberg_share = Column(Boolean, default=False, nullable=False)

    permissions = Column(JSONText)

    owner = relationship(User, foreign_keys=moderator_id)

    members = relationship("GroupMember", backref="group", cascade="all")
    addresses = relationship("GroupAddress", backref="group", cascade="all")
    forwards = relationship("GroupForward", backref="group", cascade="all")


class GroupAddress(Base):
    """Group address model."""

    __description__ = {
        'general': "An email address associated with a group. By adding "
        "an address here, all mails sent to that address will be forwarded "
        "to all members and forwards of the associated group.",
        'fields': {
            'email': "E-Mail address for the group",
        }
    }
    __expose__ = True
    __projected_fields__ = ['group']

    __owner__ = ["group.moderator_id"]
    __owner_methods__ = ['GET', 'DELETE']

    # All registered users must be able to post
    # Only way to allow moderators to create addresses
    __registered_methods__ = ['POST']

    email = Column(Unicode(100), unique=True, nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupMember(Base):
    """Group member model."""

    __description__ = {
        'general': "Assignment of registered users to groups."
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['user_id', 'group.moderator_id']
    __owner_methods__ = ['GET', 'DELETE']

    __registered_methods__ = ['POST']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


class GroupForward(Base):
    """group forward model."""

    __description__ = {
        'general': "All messages to the group will be additionally forwarded"
        "to this address The group will NOT receive messages sent to this "
        "address, see /groupaddress for this.",
        'fields': {
            'email': "E-Mail address to which mails will be forwarded"
        }
    }
    __expose__ = True
    __projected_fields__ = ['group', 'user']

    __owner__ = ['group.moderator_id']
    __owner_methods__ = ['GET', 'DELETE']

    __registered_methods__ = ['POST']

    email = Column(Unicode(100), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)


def make_groupdomain():
    """Create domain.

    This is a function so it can be called after models in all modules have
    been defined.
    """
    groupdomain = {}
    groupdomain.update(make_domain(Group))
    groupdomain.update(make_domain(GroupAddress))
    groupdomain.update(make_domain(GroupMember))
    groupdomain.update(make_domain(GroupForward))

    groupdomain['groups']['schema']['permissions'].update({
        'type': 'permissions_jsonschema'
    })

    groupdomain['groupaddresses']['schema']['group_id'].update({
        'only_groups_you_moderate': True,
        'unique_combination': ['email'],
        'not_patchable': True,
    })
    groupdomain['groupaddresses']['schema']['email'].update({
        'regex': EMAIL_REGEX,
        'unique_combination': ['group_id']})

    groupdomain['groupforwards']['schema']['group_id'].update({
        'only_groups_you_moderate': True,
        'unique_combination': ['email'],
        'not_patchable': True,
    })
    groupdomain['groupforwards']['schema']['email'].update({
        'regex': EMAIL_REGEX,
        'unique_combination': ['group_id']})

    groupdomain['groupmembers']['schema']['user_id'].update({
        'only_self_enrollment_for_group': True,
        'unique_combination': ['group_id']})
    groupdomain['groupmembers']['schema']['group_id'].update({
        'self_enrollment_must_be_allowed': True,
        'unique_combination': ['user_id']})

    # Membership is not transferable -> remove PUT and PATCH
    groupdomain['groupmembers']['item_methods'] = ['GET', 'DELETE']

    return groupdomain
