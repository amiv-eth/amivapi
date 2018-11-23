#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Install amivapi. Provide the amivapi command."""

from setuptools import setup, find_packages
import re

with open('LICENSE') as f:
    LICENSE = f.read()

# The single source of version is in the project settings.
# More: https://packaging.python.org/guides/single-sourcing-package-version/
# Parsing inspired by: https://github.com/pallets/flask/blob/master/setup.py
with open('amivapi/settings.py') as f:
    version = re.search(r'VERSION = [\'\"](.*?)[\'\"]', f.read()).group(1)

setup(
    name="amivapi",
    version=version,
    url="https://www.amiv.ethz.ch",
    author="AMIV an der ETH",
    author_email="it@amiv.ethz.ch",
    description=("The REST API behind most of AMIV's web services."),
    license=LICENSE,
    platforms=["any"],
    test_suite="amivapi.tests",
    tests_require=[],
    packages=find_packages(),
    entry_points='''
        [console_scripts]
        amivapi=amivapi.cli:cli
    '''
)
