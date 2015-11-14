#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

from setuptools import setup, find_packages

with open('LICENSE') as f:
    LICENSE = f.read()

setup(
    name="amivapi",
    version="0.1-dev",
    url="https://www.amiv.ethz.ch",
    author="AMIV an der ETH",
    author_email="it@amiv.ethz.ch",
    description=("The REST API behind most of AMIV's web services."),
    license=LICENSE,
    platforms=["any"],
    test_suite="amivapi.tests",
    tests_require=[],
    packages=find_packages(),
)
