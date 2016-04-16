# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Joboffers module.

Since there are no hooks or anything everything is just in here.
"""
from sqlalchemy import (
    Column,
    Unicode,
    CHAR,
    DateTime,
    UnicodeText)

from amivapi.utils import make_domain
from amivapi.utils import Base, register_domain


class JobOffer(Base):
    __expose__ = True

    __public_methods__ = ['GET']

    company = Column(Unicode(30))

    logo = Column(CHAR(100))  # This will be modified in schemas.py!
    pdf = Column(CHAR(100))  # This will be modified in schemas.py!
    time_end = Column(DateTime)

    title_de = Column(UnicodeText)
    title_en = Column(UnicodeText)
    description_de = Column(UnicodeText)
    description_en = Column(UnicodeText)


def make_jobdomain():
    jobdomain = make_domain(JobOffer)

    jobdomain['joboffers']['schema'].update({
        'logo': {'type': 'media', 'filetype': ['png', 'jpeg']},
        'pdf': {'type': 'media', 'filetype': ['pdf']},
    })

    return jobdomain


def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, make_jobdomain())
