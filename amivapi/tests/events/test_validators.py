# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Test general purpose validators of event module."""

import json

from amivapi.tests.utils import WebTestNoAuth


class EventValidatorTest(WebTestNoAuth):
    """Unit test class for general purpose validators of event module."""

    def test_validate_no_html(self):
        """Test no-html validator."""
        self.app.register_resource('test', {
            'schema': {
                'field': {
                    'type': 'string',
                    'no_html': True
                }
            }
        })

        has_html = '<head><title>I\'m title</title></head>Hello, <b>world</b>'
        has_no_html = 'ich <3 du und="test" d:> ichht fldf d<'

        self.api.post('/test', data={
            'field': has_html
        }, status_code=422)

        self.api.post('/test', data={
            'field': has_no_html
        }, status_code=201)

    def test_validate_json_schema_object(self):
        """Test cerberus schema validator."""
        self.app.register_resource('test', {
            'schema': {
                'field': {
                    'type': 'string',
                    'json_schema': True,
                }
            }
        })

        self.api.post('/test', data={
            'field': json.dumps({
                "random": "json",
                "things": {
                    "a": "b"
                }
            })
        }, status_code=422)

        self.api.post('/test', data={
            "field": json.dumps({
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "object",
                "additionalProperties": False,
                'properties': {
                    "field1": {
                        "type": "integer",
                        "maximum": 10
                    },
                    "field2": {
                        "type": "string"
                    }},
                "required": ["field2"]
            })
        }, status_code=201)

    def test_depends_any(self):
        """Test the depends_any validator."""
        self.app.register_resource('test', {
            'resource_methods': ['POST', 'GET'],
            'item_methods': ['GET'],
            'schema': {
                'option1': {
                    'type': 'integer'
                },
                'option2': {
                    'type': 'integer'
                },
                'needs_an_option': {
                    'type': 'integer',
                    'depends_any': ['option1', 'option2']
                }
            }
        })

        self.api.post("/test", data={'needs_an_option': 1}, status_code=422)

        self.api.post("/test", data={
            'needs_an_option': 1,
            'option1': 1
        }, status_code=201)

        self.api.post("/test", data={
            'needs_an_option': 1,
            'option2': 1
        }, status_code=201)

    def test_later_than(self):
        """Test the later_than validator."""
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'datetime'
                },
                'field2': {
                    'type': 'datetime',
                    'later_than': 'field1'
                }
            }
        })

        self.api.post("/test", data={
            'field2': '2016-10-17T10:10:10Z'
        }, status_code=201)

        self.api.post("/test", data={
            'field1': '2016-10-17T21:11:14Z',
            'field2': '2016-03-19T13:33:37Z'
        }, status_code=422)

        self.api.post("/test", data={
            'field1': '2016-10-17T21:11:14Z',
            'field2': '2017-03-19T13:33:37Z'
        }, status_code=201)

    def test_earlier_than(self):
        """Test the earlier_than validator."""
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'datetime',
                    'earlier_than': 'field2'
                },
                'field2': {
                    'type': 'datetime',
                }
            }
        })

        self.api.post("/test", data={
            'field1': '2016-10-17T10:10:10Z'
        }, status_code=201)

        self.api.post("/test", data={
            'field1': '2016-10-17T21:11:14Z',
            'field2': '2016-03-19T13:33:37Z'
        }, status_code=422)

        self.api.post("/test", data={
            'field1': '2016-10-17T21:11:14Z',
            'field2': '2017-03-19T13:33:37Z'
        }, status_code=201)

    def test_patch_time_dependencies(self):
        """Test patching time dependent fields."""
        self.app.register_resource('test', {
            'schema': {
                'time1': {
                    'type': 'datetime',
                    'earlier_than': 'time2'
                },
                'time2': {
                    'type': 'datetime',
                    'later_than': 'time1'
                }
            }
        })

        obj = self.new_object("test",
                              time1='2016-10-10T13:33:37Z',
                              time2='2016-10-20T13:33:37Z')

        headers = {'If-Match': obj['_etag']}
        url = "/test/%s" % obj['_id']

        bad_time1 = {'time1': '2016-10-25T13:33:37Z'}
        good_time1 = {'time1': '2016-10-15T13:33:37Z'}

        bad_time2 = {'time2': '2016-10-5T13:33:37Z'}
        good_time2 = {'time2': '2016-10-26T13:33:37Z'}

        for bad in bad_time1, bad_time2:
            self.api.patch(url, headers=headers, data=bad, status_code=422)

        for good in good_time1, good_time2:
            r = self.api.patch(url, headers=headers,
                               data=good, status_code=200).json
            # Update etag for next request
            headers['If-Match'] = r['_etag']

    def test_only_if_not_null(self):
        """Test that the only_if_not_null validator works."""
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'integer',
                },
                'field2': {
                    'type': 'integer',
                    'only_if_not_null': 'field1'
                }
            }
        })

        self.api.post('/test', data={}, status_code=201)

        self.api.post('/test', data={
            'field1': 1
        }, status_code=201)

        self.api.post('/test', data={
            'field2': 1
        }, status_code=422)

        self.api.post('/test', data={
            'field1': 1,
            'field2': 1,
        }, status_code=201)

        # If the values would have a negative boolean value it
        # should still work
        self.api.post('/test', data={
            'field1': 0,
            'field2': 1,
        }, status_code=201)

    def test_only_if_not_null_patch(self):
        """Test that patches check the original document."""
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'integer',
                },
                'field2': {
                    'type': 'integer',
                    'only_if_not_null': 'field1'
                }
            }
        })

        response = self.api.post('/test', data={
            'field1': 1
        }, status_code=201).json

        self.api.patch(
            '/test/%s' % response['_id'],
            data={'field2': 1},
            headers={'If-Match': response['_etag']},
            status_code=200
        )

    def test_can_add_time_for_later_than(self):
        """Test issue #141.

        The validator later_than assumed, that the field is
        already existing on PATCH requests. Check that this is fixed.
        """
        self.app.register_resource('test', {
            'schema': {
                'time1': {
                    'type': 'datetime'
                },
                'time2': {
                    'type': 'datetime',
                    'later_than': 'time1'
                }
            }
        })

        obj = self.new_object("test")

        data = {
            'time1': "2016-01-01T00:00:00Z",
            'time2': "2016-02-02T00:00:00Z"
        }
        self.api.patch('/test/%s' % obj['_id'], data=data,
                       headers={'If-Match': obj['_etag']},
                       status_code=200)

    def test_required_if_not(self):
        """Test required_if_not validator."""
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'integer',
                    'required_if_not': 'field2'
                },
                'field2': {
                    'type': 'integer',
                    'required_if_not': 'field1'
                }
            }
        })

        self.api.post('/test', data={}, status_code=422)
        self.api.post('/test', data={'field1': 1}, status_code=201)
        self.api.post('/test', data={'field2': 1}, status_code=201)
        self.api.post('/test', data={'field1': 1, 'field2': 2}, status_code=201)

    def test_validator_order(self):
        """Test to show issue #176: The later_than validator can crash, as the
        type of the target may not have been checked."""
        self.app.register_resource('test', {
            'schema': {
                'field1': {
                    'type': 'datetime',
                    'later_than': 'field2'
                },
                'field2': {
                    'type': 'datetime'
                }
            }
        })

        resp = self.api.post("/test", data={
            'field1': '2017-01-01T13:33:37Z',
            'field2': '2017-00-00T13:33:37Z'
        }, status_code=422)

        assert 'exception' not in resp.json['_issues']
