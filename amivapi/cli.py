# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""A command line interface for AMIVApi."""

from base64 import b64encode
from datetime import datetime as dt
from os import urandom

from click import argument, echo, File, group, option, Path
from ruamel import yaml

from amivapi.bootstrap import create_app
from amivapi.cron import run_scheduled_tasks
from amivapi import ldap
from amivapi.settings import DEFAULT_CONFIG_FILENAME, FORWARD_DIR


@group()
def cli():
    """Manage amivapi."""


config_option = option("--config",
                       type=Path(exists=True, dir_okay=False, readable=True),
                       help="use specified config file")


@cli.command()
@config_option
def cron(config):
    """Run scheduled tasks."""
    app = create_app(config) if config else create_app()
    with app.app_context():
        run_scheduled_tasks()


@cli.command()
@config_option
@option('--all', 'sync_all', is_flag=True, help="Sync all users.")
@argument('nethz', nargs=-1)
def ldap_sync(config, sync_all, nethz):
    """Synchronize users with eth ldap.

    Examples:

        amivapi ldap_sync --all

        amivapi ldap_sync adietmue bconrad blumh
    """
    app = create_app(config) if config else create_app()
    if not app.config['ENABLE_LDAP']:
        echo("LDAP is not enabled, can't proceed!")
    else:
        with app.test_request_context():
            if sync_all:
                res = ldap.sync_all()
                echo("Synchronized %i users." % len(res))
            else:
                for user in nethz:
                    if ldap.sync_one(user) is not None:
                        echo("Succesfully synchronized '%s'." % user)
                    else:
                        echo("Could not synchronize '%s'." % user)


@cli.command()
@config_option
def run(config):
    """Start amivapi development server."""
    app = create_app(config) if config else create_app()

    app.run(threaded=True)


def no_prompts(ctx, param, value):
    """Deactivate prompting completely."""
    if value:  # enable_ldap == False
        for opt in ctx.command.params:
            opt.prompt = None
    return value


def no_ldap_prompts(ctx, param, value):
    """Deactivate prompting for ldap user and password."""
    if not value:  # enable_ldap == False
        for opt in ctx.command.params:
            if opt.name in ['LDAP_USER', 'LDAP_PASS']:
                opt.prompt = None
    return value


@cli.command()
# Turn off all prompts (defaults will be used)
@option("--no-prompts", is_flag=True, is_eager=True, expose_value=False,
        callback=no_prompts, help="Do not prompt user for input.")
# Server settings
@option("--root-password", "ROOT_PASSWORD", default="root",
        prompt="AMIVAPI root password.",
        help="Root Password.")
@option("--debug/--no-debug", "DEBUG", default=False,
        prompt="Enable debug mode",
        help="Debug mode on/off.")
# Email settings
@option("--smtp", "SMTP_SERVER", default="localhost",
        prompt="STMP server for outgoing mails",
        help="SMTP server.")
@option("--mail", "API_MAIL", default="api@amiv.ethz.ch",
        prompt="E-mail address for outgoing mails",
        help="Api mail address.")
# Database settings
@option("--mongo-host", "MONGO_HOST", default='localhost',
        prompt="MongoDB hostname",
        help="MongoDB hostname.")
@option("--mongo-port", "MONGO_PORT", default=27017,
        prompt="MongoDB port",
        help="MongoDB port.")
@option("--mongo-username", "MONGO_USERNAME", default="",
        prompt="MongoDB username",
        help="MongoDB username.")
@option("--mongo-password", "MONGO_PASSWORD", default="",
        prompt="MongoDB password",
        help="MongoDB password.")
@option("--mongo-dbname", "MONGO_DBNAME", default='amivapi',
        prompt="MongoDB database name",
        help="MongoDB database name.")
# Storage settings
@option("--forward-dir", "FORWARD_DIR", default=FORWARD_DIR,
        type=Path(file_okay=False, resolve_path=True),
        prompt="Directory to store mailing list files",
        help="Forward directory.")
# LDAP settings
@option("--ldap/--no-ldap", "ENABLE_LDAP", default=False,
        callback=no_ldap_prompts,
        prompt="Enable LDAP",
        help="LDAP on/off.")
@option("--ldap-user", "LDAP_USER",
        prompt="LDAP username",
        help="LDAP username.")
@option("--ldap-pass", "LDAP_PASS",
        prompt="LDAP password",
        help="LDAP password.")
# Specify config file (optional)
@argument("config_file", type=File('w'), default=DEFAULT_CONFIG_FILENAME)
def create_config(config_file, **data):
    """Generate a config file."""
    # Add secret for token generation
    data['TOKEN_SECRET'] = b64encode(urandom(32)).decode('utf_8')
    if 'DEBUG' in data:
        data['TESTING'] = True  # Eve debug info
    if not data['ENABLE_LDAP']:
        # Don't put those keys in config if disabled
        del data['LDAP_USER']
        del data['LDAP_PASS']

    config_file.write("# Automatically generated on %s\n\n" % dt.utcnow())
    yaml.safe_dump(data, config_file, default_flow_style=False)
