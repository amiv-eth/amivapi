# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Sentry integration tests."""

from os import getenv
import warnings

from flask.signals import got_request_exception

from amivapi.tests.utils import WebTestNoAuth, skip_if_false

# Get test dsn from environment
SENTRY_DSN = getenv('SENTRY_TEST_DSN')


class SentryIntegrationTest(WebTestNoAuth):
    """Raise an error to check if it gets sent to Sentry."""

    def setUp(self, *args, **kwargs):
        """Extended setUp: Move environment variables to config."""
        extra_config = {
            'SENTRY_DSN': SENTRY_DSN,
            'SENTRY_ENVIRONMENT': 'testing',
        }
        extra_config.update(kwargs)
        super().setUp(*args, **extra_config)

    @skip_if_false(SENTRY_DSN, "Sentry test requires environment variable "
                               "'SENTRY_TEST_DSN'")
    def test_sentry(self):
        """Just raise an exception. You need to check sentry manually!"""
        exception = Exception('This is a test! If this messages is '
                              'received, everything works as intended.')

        # Sentry subscribes to flask signals, so send a test signal
        got_request_exception.send(self, exception=exception)

        warnings.warn(UserWarning('Please verify with Sentry that the '
                                  'test error was received.'))
