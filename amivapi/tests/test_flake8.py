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
