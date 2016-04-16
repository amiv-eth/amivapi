# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Session endpoints."""

from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Text)

from amivapi.utils import Base, make_domain


class Session(Base):
    """Session model."""

    __description__ = {
        'general': "A session is used to authenticate a user after he "
        " provided login data. To acquire a session use POST, which will "
        " give you a token to use as the user field of HTTP basic auth "
        " header with an empty password. POST requires user and password "
        " fields.",
        'methods': {
            'POST': "Login and aquire a login token. Post the fields "
            "'user' and 'password', the response will contain the token."
        }
    }
    __expose__ = True
    __projected_fields__ = ['user']

    __public_methods__ = ['POST']
    __owner__ = ['user_id']
    __owner_methods__ = ['GET', 'DELETE']

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(Text)


def make_sessiondomain():
    """Create domain.

    This is a function so it can be called after models in all modules have
    been defined.
    """
    sessiondomain = {}

    sessiondomain.update(make_domain(Session))

    sessiondomain['sessions']['schema']['user'] = {
        'type': 'string',
        'required': True,
        'nullable': False,
        'empty': False
    }
    sessiondomain['sessions']['schema']['password'] = {
        'type': 'string',
        'required': True,
        'nullable': False,
        'empty': False
    }
    sessiondomain['sessions']['schema']['user_id'].update({
        'readonly': True,
        'required': False,
    })
    sessiondomain['sessions']['schema']['token'].update({
        'readonly': True,
        'required': False
    })

    return sessiondomain
