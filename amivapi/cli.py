#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""A command line interface for AMIVApi."""

from os import urandom
from base64 import b64encode
from datetime import datetime as dt
from click import group, option, argument, Path, File
from ruamel import yaml

from amivapi.bootstrap import create_app
from amivapi.settings import DEFAULT_CONFIG_FILENAME


@group()
def cli():
    """Manage amivapi."""


@cli.command()
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None)
def run(config):
    """Start amivapi development server."""
    app = create_app(config) if config else create_app()

    app.run()


def no_ldap_prompts(ctx, param, value):
    """Deactivate prompting for ldap user and password."""
    if not value:  # enable_ldap == False
        for opt in ctx.command.params:
            if opt.name in ['LDAP_USER', 'LDAP_PASS']:
                opt.prompt = None
    return value


@cli.command()
# Server settings
@option("--server", "SERVER_NAME", prompt=True, default="localhost")
@option("--debug/--no-debug", "DEBUG", default=False, prompt=True)
# Email settings
@option("--smtp", "SMTP_SERVER", default="localhost",
        prompt=True)
@option("--mail", "API_MAIL", default="api@amiv.ethz.ch",
        prompt=True)
# Database settings
@option("--mongo-host", "MONGO_HOST", default='localhost',
        prompt=True)
@option("--mongo-port", "MONGO_PORT", default=27017,
        prompt=True)
@option("--mongo-username", "MONGO_USERNAME", default="",
        prompt=True)
@option("--mongo-password", "MONGO_PASSWORD", default="",
        prompt=True)
@option("--mongo-dbname", "MONGO_DBNAME", default='amivapi',
        prompt=True)
# LDAP settings
@option("--ldap/--no-ldap", "ENABLE_LDAP", default=False,
        prompt=True, callback=no_ldap_prompts)
@option("--ldap-user", "LDAP_USER",
        prompt=True)
@option("--ldap-pass", "LDAP_PASS",
        prompt=True)
# Specify config file (optional)
@argument("config", type=File('w'), default=DEFAULT_CONFIG_FILENAME)
def create_config(config, **data):
    """Generate a config file."""
    # Add secret for token generation
    data['TOKEN_SECRET'] = b64encode(urandom(32)).decode('utf_8')
    if 'DEBUG' in data:
        data['TESTING'] = True  # Eve debug info
    if not data['ENABLE_LDAP']:
        # Don't put those keys in config if disabled
        del data['LDAP_USER']
        del data['LDAP_PASS']

    config.write("# Automatically generated on %s\n\n" % dt.utcnow())
    yaml.safe_dump(data, config, default_flow_style=False)
