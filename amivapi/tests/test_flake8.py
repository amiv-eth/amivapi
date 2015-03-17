# -*- coding: utf-8 -*-
#
# AMIVAPI test_flake8.py
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

from unittest import TestCase
from flake8.engine import get_style_guide
from flake8.main import print_report

from amivapi.settings import ROOT_DIR


class TestFlake8(TestCase):

    def test_flake8(self):

        flake8 = get_style_guide(exclude=['.tox', 'build'])
        report = flake8.check_files([ROOT_DIR])
        exit_code = print_report(report, flake8)
        self.assertTrue(exit_code == 0)
