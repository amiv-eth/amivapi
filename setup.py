#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# AMIVAPI setup.py
# Copyright (C) 2015 AMIV an der ETH, see AUTHORS for more details
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    tests_require=['pillow'],
    packages=find_packages(),
)
