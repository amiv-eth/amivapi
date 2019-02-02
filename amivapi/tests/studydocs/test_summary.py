# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Tests for studydocuments summaries."""

import json

from amivapi.tests.utils import WebTestNoAuth


class StudydocsSummaryTest(WebTestNoAuth):
    """Studycos Test class."""

    def _load_data(self):
        """Load some test fixtures."""
        self.load_fixture({
            'studydocuments': [{
                'title': 'first',
                'lecture': 'a',
                'professor': 'a',
            }, {
                'title': 'second',
                'lecture': 'a',
                'professor': 'b',
            }, {
                'title': 'third',
                'professor': 'b',
            }]
        })

    def test_full_summary(self):
        """Test returning a summary."""
        self._load_data()

        response = self.api.get("/studydocuments?summary",
                                status_code=200).json

        assert '_summary' in response
        assert response['_summary'] == {
            'lecture': {
                'a': 2,
            },
            'professor': {
                'a': 1,
                'b': 2,
            }
        }

    def test_filtered_summary(self):
        """The summary is only computed for the matched documents."""
        self._load_data()
        match = json.dumps({'title': {'$in': ['first', 'second']}})

        response = self.api.get("/studydocuments?where=%s" % match,
                                status_code=200).json

        assert '_summary' in response
        assert response['_summary'] == {
            'lecture': {
                'a': 2,
            },
            'professor': {
                'a': 1,
                'b': 1,  # The document with title `third` is ignored
            }
        }
