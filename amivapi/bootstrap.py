# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""API factory."""

from os import getcwd, getenv
from os.path import abspath

from eve import Eve
from flask import Config

from amivapi import (
    auth,
    beverages,
    cascade,
    cron,
    documentation,
    events,
    groups,
    joboffers,
    ldap,
    studydocs,
    users,
    utils
)
from amivapi.validation import ValidatorAMIV


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

    config.update(kwargs)

    app = Eve(settings=config,
              validator=ValidatorAMIV)
    app.logger.info(config_status)

    # Create LDAP connector
    ldap.init_app(app)

    # Initialize modules to register resources, validation, hooks, auth, etc.
    users.init_app(app)
    auth.init_app(app)
    events.init_app(app)
    groups.init_app(app)
    joboffers.init_app(app)
    beverages.init_app(app)
    studydocs.init_app(app)
    cascade.init_app(app)
    cron.init_app(app)
    documentation.init_app(app)

    # Fix that eve doesn't run hooks on embedded documents
    app.on_fetched_item += utils.run_embedded_hooks_fetched_item
    app.on_fetched_resource += utils.run_embedded_hooks_fetched_resource

    return app
