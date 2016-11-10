# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""A command line interface for AMIVApi."""

from os import urandom
from base64 import b64encode
from datetime import datetime as dt
from click import group, option, argument, Path, File, prompt
from ruamel import yaml

from amivapi.bootstrap import create_app
from amivapi.settings import DEFAULT_CONFIG_FILENAME, STORAGE_DIR, FORWARD_DIR


@group()
def cli():
    """Manage amivapi."""


def change_apikey_prompt(config, current_permissions):
    """ Prompt for changes to the permissions described by current_permissions
    """

    # We need to create an app to get a list of resources available
    app = create_app(config) if config else create_app()
    resources = list(app.config['DOMAIN'].keys())

    while True:
        print("Current permissions:")
        print(current_permissions)
        print("")
        print("Available resources:")
        print(", ".join(resources))
        resource = prompt("Change permissions of what resource? \"x\" to exit",
                          default="x")
        if resource == "x":
            break

        if resource not in resources:
            print("Unknown resource")
            continue

        method = prompt("Which method to toggle"
                        "(GET, POST, PATCH, PUT, DELETE)?", default="")

        if method in ['GET', 'POST', 'PATCH', 'PUT', 'DELETE']:
            if method in current_permissions.get(resource, []):
                current_permissions[resource].remove(method)
                if not current_permissions[resource]:
                    current_permissions.remove(resource)
            else:
                if resource not in current_permissions:
                    current_permissions[resource] = []
                current_permissions[resource].append(method)
        else:
            print("Unknown method")


@cli.command()
@option("--name", "name", prompt="Key name", help="Name of the key")
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None,
        help="use specified config file")
def apikeys_add(name, config):
    """ Add a new apikey to the apikey file """
    try:
        with open('apikeys.yaml', 'r') as apikey_file:
            apikeys = yaml.load(apikey_file)
    except IOError:
        apikeys = {}

    for token, apikey_data in apikeys.items():
        if apikey_data['NAME'] == name:
            print("A key with that name already exists!")
            return

    token = b64encode(urandom(32)).decode('utf_8')

    current_permissions = {}
    change_apikey_prompt(config, current_permissions)

    apikeys[token] = {
        'NAME': name,
        'PERMISSIONS': current_permissions
    }

    with open('apikeys.yaml', 'w') as apikey_file:
        yaml.safe_dump(apikeys, apikey_file, default_flow_style=False)


@cli.command()
@option("--name", "name", prompt="Key name", help="Name of the key")
def apikeys_delete(name):
    """ Delete an apikey """
    try:
        with open('apikeys.yaml', 'r') as apikey_file:
            apikeys = yaml.load(apikey_file)
    except IOError:
        print("No apikeys set.")
        return

    token_to_delete = None
    for token, apikey_data in apikeys.items():
        if apikey_data['NAME'] == name:
            token_to_delete = token

    if token_to_delete is None:
        print("No such key.")
        return

    del apikeys[token_to_delete]

    with open('apikeys.yaml', 'w') as apikey_file:
        yaml.safe_dump(apikeys, apikey_file, default_flow_style=False)


@cli.command()
@option("--name", "name", prompt="Key name", help="Name of the key")
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None,
        help="use specified config file")
def apikeys_change(name, config):
    """ Change the permissions of an existing apikey """
    try:
        with open('apikeys.yaml', 'r') as apikey_file:
            apikeys = yaml.load(apikey_file)
    except IOError:
        print("No apikeys set.")
        return

    token_to_edit = None
    for token, apikey_data in apikeys.items():
        if apikey_data['NAME'] == name:
            token_to_edit = token

    if token_to_edit is None:
        print("No such key.")
        return

    change_apikey_prompt(config, apikeys[token_to_edit]['PERMISSIONS'])

    with open('apikeys.yaml', 'w') as apikey_file:
        yaml.safe_dump(apikeys, apikey_file, default_flow_style=False)


@cli.command()
def apikeys_list():
    """ Show existing apikeys """
    try:
        with open('apikeys.yaml', 'r') as apikey_file:
            apikeys = yaml.load(apikey_file)
    except IOError:
        print("No apikeys set.")
        return

    for token, apikey_data in apikeys.items():
        print("%s: %s" % (apikey_data['NAME'], token))
        print("    %s" % apikey_data['PERMISSIONS'])


@cli.command()
@option("--config", type=Path(exists=True, dir_okay=False, readable=True),
        default=None,
        help="use specified config file")
def cron(config):
    app = create_app(config) if config else create_app()
    with app.app_context():
        run_scheduled_tasks()


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
