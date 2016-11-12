# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""A command line interface for AMIVApi."""

from os import urandom
from base64 import b64encode
from datetime import datetime as dt
from click import (
    Choice, echo, group, option, argument, Path, File, BadParameter,
    pass_context, pass_obj, ParamType, confirmation_option)
from ruamel import yaml

from amivapi.bootstrap import create_app
from amivapi.settings import DEFAULT_CONFIG_FILENAME, STORAGE_DIR, FORWARD_DIR


@group()
def cli():
    """Manage amivapi."""


@cli.command()
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None, help="use specified config file")
def cron(config):
    """Run scheduled tasks."""
    app = create_app(config) if config else create_app()
    with app.app_context():
        run_scheduled_tasks()


@cli.group()
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None, help="use specified config file")
@pass_context
def apikeys(ctx, config):
    """Manage amivapi apikeys."""
    # Set the app as ctx.obj, then we can use the @pass_obj decorator to get it
    ctx.obj = create_app(config) if config else create_app()

    # Automatically safe keys after commands finish (call_on_close)
    def _safe_keys():
        with open('apikeys.yaml', 'w') as apikey_file:
            yaml.safe_dump(ctx.obj.config['APIKEYS'], apikey_file,
                           default_flow_style=False)
    ctx.call_on_close(_safe_keys)


class _Res(ParamType):
    name = 'resource'

    def convert(self, value, param, ctx):
        if value not in ctx.obj.config['DOMAIN']:
            self.fail("'%s' is not an amivapi resource." % value, param, ctx)
        return value


class _Key(ParamType):
    name = 'apikey'

    def convert(self, value, param, ctx):
        if value not in ctx.obj.config['APIKEYS']:
            self.fail("Apikey '%s' doesn't exist." % value, param, ctx)
        return value


def _unique(ctx, param, value):
    for keydata in ctx.obj.config['APIKEYS'].values():
        if value == keydata['token']:
            raise BadParameter("Token already exists.")
    return value


@apikeys.command()
@pass_obj  # obj is the app
def list(app):
    """List all apikeys."""
    if app.config['APIKEYS']:
        echo(yaml.dump(app.config['APIKEYS'], default_flow_style=False))
    else:
        echo('There are no apikeys.')


@apikeys.command()
@option('-t', '--token', help="The apikey auth token.", callback=_unique,
        default=lambda: b64encode(urandom(64)).decode('utf_8'))
@option('-p', '--permission', type=(_Res(), Choice(['read', 'readwrite'])),
        help="Permissions for a resource, can either be 'read' or 'readwrite'."
        " This option can be used multiple times.", multiple=True)
@argument('keyname')
@pass_obj
def add(app, permission, keyname, token):
    """Add an apikey, overwrite if it exists already.

    Example:

        amivapi apikeys add Bierkey -p users read -p purchases readwrite
    """
    app.config['APIKEYS'][keyname] = {
        'token': token,
        'permissions': {res: perm for (res, perm) in permission}}


@apikeys.command()
@option('-t', '--token', help="New apikey auth token.", callback=_unique)
@option('-p', '--permission', type=(_Res(), Choice(['read', 'readwrite'])),
        help="Permissions for a resource, can either be 'read' or 'readwrite'."
        " This option can be used multiple times.", multiple=True)
@option('-r', '--remove', multiple=True, type=_Res(),
        help="Remove permissions for a resource. Can be used multiple times.")
@argument('keyname', type=_Key())
@pass_obj
def update(app, token, permission, remove, keyname):
    """Update an apikey.

    Add or remove permissions. If both is specified, add overwrites remove.

    Example:

        amivapi apikeys update Bierkey -r users -p groups read
    """
    apikey = app.config['APIKEYS'][keyname]  # safe because key must exist
    if token:
        apikey['token'] = token
    for key in remove:
        apikey['permissions'].pop(key, None)
    for res, perm in permission:
        apikey['permissions'][res] = perm


@apikeys.command()
@confirmation_option(prompt="Do you really want to delete this apikey?")
@argument('keyname', type=_Key())
@pass_obj
def remove(app, keyname):
    """Remove an apikey."""
    app.config['APIKEYS'].pop(keyname, None)


@cli.command()
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None,
        help="use specified config file")
def run(config):
    """Start amivapi development server."""
    app = create_app(config) if config else create_app()

    app.run(threaded=True)


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
