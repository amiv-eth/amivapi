# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""API factory."""

from os import getcwd

from flask import Config
from eve import Eve
# from eve_docs import eve_docs

from amivapi import (
    users,
    auth,
    events,
    # media,
    # groups,
    # documentation,
    utils,
    # joboffers,
    purchases,
    # studydocs
)
from amivapi.ldap import ldap_connector
from amivapi import cascade


def create_app(config_file='mongo_config.cfg', **kwargs):
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
    config = Config(getcwd())
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile(config_file)
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                      "`python manage.py create_config`.")
    config.update(kwargs)

    # config['BLUEPRINT_DOCUMENTATION'] = documentation.get_blueprint_doc()
    app = Eve(settings=config,
              validator=utils.ValidatorAMIV)

    # TODO(Alex): media=media.FileSystemStorage)

    # What is this good for? Seems to change nothing if commented out
    # Bootstrap(app)

    # Create LDAP connector
    if app.config['ENABLE_LDAP']:
        ldap_connector.init_app(app)

    # Generate and expose docs via eve-docs extension
    # app.register_blueprint(eve_docs, url_prefix="/docs")

    # Initialize modules to register resources, validation, hooks, auth, etc.
    users.init_app(app)
    auth.init_app(app)
    events.init_app(app)
    # groups.init_app(app)
    # joboffers.init_app(app)
    purchases.init_app(app)
    # studydocs.init_app(app)
    # media.init_app(app)

    # Register hooks for cascading deletes
    app.on_deleted_item += cascade.cascade_delete
    app.on_deleted += cascade.cascade_delete_collection

    return app
