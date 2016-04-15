# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Purchases module.

Since there are no hooks or anything everything is just in here.
"""
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Enum,
    DateTime)

from amivapi.utils import make_domain
from amivapi.utils import Base, register_domain


class Purchase(Base):
    """Purchase model."""

    __description__ = {
        'general': "A beer machine or kaffi machine transaction. Users should"
        " be able to get beer or kaffi, if their last timestamp is older than"
        " one day and they are AMIV members. This resource is used to log"
        " their purchases.",
        'fields': {
            'slot': "Slot in the machine which was purchased(different items,"
            " which may have different prices)."
        }
    }
    __expose__ = True

    __owner__ = ['user_id']
    __owner_methods__ = ['GET']

    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime)
    type = Column(Enum("beer", "kaffi"))
    slot = Column(Integer)


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_domain(Purchase))
