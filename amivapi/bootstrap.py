# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""API factory."""

from os import getcwd, getenv
from os.path import abspath

from eve import Eve
from flask import Config

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from amivapi import (
    auth,
    cascade,
    cron,
    documentation,
    events,
    groups,
    blacklist,
    joboffers,
    ldap,
    studydocs,
    users,
    utils
)
from amivapi.validation import ValidatorAMIV


def init_sentry(app):
    """Init sentry if DSN *and* environment are provided."""
    dsn = app.config['SENTRY_DSN']
    env = app.config['SENTRY_ENVIRONMENT']

    if dsn is None and env is None:
        return

    if None in (dsn, env):
        raise ValueError("You need to specify both DSN and environment "
                         "to use Sentry.")

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=env,
    )


SIP_ENV_VARS = [
    'SIP_AUTH_OIDC_DISCOVERY_URL',
    'SIP_AUTH_AMIVAPI_CLIENT_ID',
    'SIP_AUTH_AMIVAPI_CLIENT_SECRET',
]


def get_sip_config_from_env():
    """Read the SIP configuration from environment variables."""
    return {varname: getenv(varname) for varname in SIP_ENV_VARS}


def drop_none_values_from_dict(dic):
    """Drops all key-value pairs from a dictionary that have a None value."""
    return {k: v for k, v in dic.items() if v is not None}


def create_app(config_file=None, **kwargs):
    """
    Create a new eve app object and initialize everything.

    User configuration can be loaded in the following order:

    1. Use the `config_file` arg to specify a file
    2. If `config_file` is `None`, you set the environment variable
       `AMIVAPI_CONFIG` to the path of your config file
    3. If no environment variable is set either, `config.py` in the current
       working directory is used

    Args:
        config (path): Specify config file to use.
        kwargs: All other key-value arguments will be used to update the config
    Returns:
        (Eve): The Eve application
    """
    # Load config
    config = Config(getcwd())
    config.from_object("amivapi.settings")

    # Specified path > environment var > default path; abspath for better log
    user_config = abspath(config_file or getenv('AMIVAPI_CONFIG', 'config.py'))
    try:
        config.from_pyfile(user_config)
        config_status = "Config loaded: %s" % user_config
    except IOError:
        config_status = "No config found."

    # The SIP container is passing us settings through environment variables.
    sip_env_config = get_sip_config_from_env()
    # Unset environment variables will be be None values. In those cases we
    # will want to keep the default, which is ok for testing.
    config_updates = drop_none_values_from_dict(sip_env_config)
    config.update(config_updates)

    config.update(kwargs)

    # Initialize empty domain to create Eve object, register resources later
    config['DOMAIN'] = {}

    app = Eve("amivapi",  # Flask needs this name to find the static folder
              settings=config,
              validator=ValidatorAMIV)
    app.logger.info(config_status)

    # Set up error logging with sentry
    init_sentry(app)

    # Create LDAP connector
    ldap.init_app(app)

    # Initialize modules to register resources, validation, hooks, auth, etc.
    users.init_app(app)
    auth.init_app(app)
    events.init_app(app)
    groups.init_app(app)
    blacklist.init_app(app)
    joboffers.init_app(app)
    studydocs.init_app(app)
    cascade.init_app(app)
    cron.init_app(app)
    documentation.init_app(app)

    # Fix that eve doesn't run hooks on embedded documents
    app.on_fetched_item += utils.run_embedded_hooks_fetched_item
    app.on_fetched_resource += utils.run_embedded_hooks_fetched_resource

    return app
