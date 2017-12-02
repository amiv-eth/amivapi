# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""API factory."""

from os import getcwd

from eve import Eve
from flask import Config
from ruamel import yaml

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
    media,
    studydocs,
    users,
    utils
)
from amivapi.settings import DEFAULT_CONFIG_FILENAME


def create_app(config_file=DEFAULT_CONFIG_FILENAME, **kwargs):
    """
    Create a new eve app object and initialize everything.

    Args:
        config (path or dict): If dict, use directly to update config, if its
            a path load the file and update config.
            If no config is provided, attemp to find it in the current working
            directory
        kwargs: All other key-value arguments will be used to update the config
    Returns:
        (Eve): The Eve application
    """
    # Load config
    config = Config(getcwd())
    config.from_object("amivapi.settings")
    try:
        with open(config_file, 'r') as f:
            yaml_data = yaml.load(f)
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                      "`amivapi create_config`.")
    else:
        config.update(yaml_data)

    config.update(kwargs)

    app = Eve(settings=config,
              validator=utils.ValidatorAMIV,
              media=media.FileSystemStorage)

    # Create LDAP connector
    if app.config['ENABLE_LDAP']:
        ldap.init_app(app)

    # Initialize modules to register resources, validation, hooks, auth, etc.
    users.init_app(app)
    auth.init_app(app)
    events.init_app(app)
    groups.init_app(app)
    joboffers.init_app(app)
    beverages.init_app(app)
    studydocs.init_app(app)
    media.init_app(app)
    cascade.init_app(app)
    cron.init_app(app)
    documentation.init_app(app)

    # Fix that eve doesn't run hooks on embedded documents
    app.on_fetched_item += utils.run_embedded_hooks_fetched_item
    app.on_fetched_resource += utils.run_embedded_hooks_fetched_resource

    return app
