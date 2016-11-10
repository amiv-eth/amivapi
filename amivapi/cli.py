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
from amivapi.settings import DEFAULT_CONFIG_FILENAME, STORAGE_DIR, FORWARD_DIR


@group()
def cli():
    """Manage amivapi."""


@cli.command()
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None,
        help="use specified config file")
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
@option("--debug/--no-debug", "DEBUG", default=False,
        prompt="Enable debug mode",
        help="debug mode on/off")
# Email settings
@option("--smtp", "SMTP_SERVER", default="localhost",
        prompt="STMP server for outgoing mails",
        help="SMTP server")
@option("--mail", "API_MAIL", default="api@amiv.ethz.ch",
        prompt="E-mail address for outgoing mails",
        help="api mail address")
# Database settings
@option("--mongo-host", "MONGO_HOST", default='localhost',
        prompt="MongoDB hostname",
        help="MongoDB hostname")
@option("--mongo-port", "MONGO_PORT", default=27017,
        prompt="MongoDB port",
        help="MongoDB port")
@option("--mongo-username", "MONGO_USERNAME", default="",
        prompt="MongoDB username",
        help="MongoDB username")
@option("--mongo-password", "MONGO_PASSWORD", default="",
        prompt="MongoDB password",
        help="MongoDB password")
@option("--mongo-dbname", "MONGO_DBNAME", default='amivapi',
        prompt="MongoDB database name",
        help="MongoDB database name")
# Storage settings
@option("--storage-dir", "STORAGE_DIR", default=STORAGE_DIR,
        type=Path(file_okay=False, resolve_path=True),
        prompt="Directory to store all file uploads",
        help="file storage directory")
@option("--forward-dir", "FORWARD_DIR", default=FORWARD_DIR,
        type=Path(file_okay=False, resolve_path=True),
        prompt="Directory to store mailing list files",
        help="forward directory")
# LDAP settings
@option("--ldap/--no-ldap", "ENABLE_LDAP", default=False,
        callback=no_ldap_prompts,
        prompt="Enable LDAP",
        help="LDAP on/off")
@option("--ldap-user", "LDAP_USER",
        prompt="LDAP username",
        help="LDAP username")
@option("--ldap-pass", "LDAP_PASS",
        prompt="LDAP password",
        help="LDAP password")
# Specify config file (optional)
@argument("file", type=File('w'), default=DEFAULT_CONFIG_FILENAME)
def create_config(file, **data):
    """Generate a config file."""
    # Add secret for token generation
    data['TOKEN_SECRET'] = b64encode(urandom(32)).decode('utf_8')
    if 'DEBUG' in data:
        data['TESTING'] = True  # Eve debug info
    if not data['ENABLE_LDAP']:
        # Don't put those keys in config if disabled
        del data['LDAP_USER']
        del data['LDAP_PASS']

    file.write("# Automatically generated on %s\n\n" % dt.utcnow())
    yaml.safe_dump(data, file, default_flow_style=False)
