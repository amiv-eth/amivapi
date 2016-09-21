# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""API factory."""

from eve import Eve
# from eve_docs import eve_docs
# from flask.ext.bootstrap import Bootstrap

from amivapi import (
    users,
    auth,
    # events,
    # media,
    # groups,
    # ldap,
    # documentation,
    utils,
    # joboffers,
    # purchases,
    studydocs
)
from amivapi.ldap import ldap_connector

from amivapi.utils import get_config


def create_app(**kwargs):
    """
    Create a new eve app object and initialize everything.

    :param disable_auth: This can be used to allow every request without
                         authentication for testing purposes
    :param **kwargs: All other parameters overwrite config values
    :returns: eve.Eve object, the app object
    """
    config = get_config()
    # Unless specified start with empty domain and add resources later
    config.setdefault('DOMAIN', {})
    # config['BLUEPRINT_DOCUMENTATION'] = documentation.get_blueprint_doc()
    config.update(kwargs)

    app = Eve(settings=config,
              validator=utils.ValidatorAMIV)

    # TODO(Alex): media=media.FileSystemStorage)

    # What is this good for? Seems to change nothing if commented out
    # Bootstrap(app)

    # Create LDAP connector
    # if config['ENABLE_LDAP']:
    #    app.ldap_connector = ldap.LdapConnector(config['LDAP_USER'],
    #                                            config['LDAP_PASS'])

    # Generate and expose docs via eve-docs extension
    # app.register_blueprint(eve_docs, url_prefix="/docs")

    # Initialize modules to register resources, validation, hooks, auth, etc.
    users.init_app(app)
    auth.init_app(app)
    # events.init_app(app)
    # groups.init_app(app)
    # joboffers.init_app(app)
    # purchases.init_app(app)
    studydocs.init_app(app)
    # media.init_app(app)

    return app
