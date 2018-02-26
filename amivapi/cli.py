# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""A command line interface for AMIVApi."""
from os import listdir, remove
from os.path import join, isdir

from click import argument, echo, group, option, Path

from amivapi.bootstrap import create_app
from amivapi.cron import run_scheduled_tasks
from amivapi import ldap
from amivapi.groups.mailing_lists import update_group


@group()
def cli():
    """Manage amivapi."""


config_option = option("--config",
                       type=Path(exists=True, dir_okay=False, readable=True),
                       help="use specified config file")


@cli.command()
@config_option
def recreate_mailing_lists(config):
    """(Re-)create mailing lists for all groups.

    1. Delete all mailing list files.

    2. Create new mailing list files.

    For every group, we call the update_group function for this
    """
    app = create_app(config_file=config)
    directory = app.config.get('MAILING_LIST_DIR')
    prefix = app.config['MAILING_LIST_FILE_PREFIX']

    if not directory:
        echo('No directory for mailing lists specified in config.')
        return

    # Delete existing files
    if isdir(directory):
        for filename in listdir(directory):
            if filename.startswith(prefix):
                remove(join(directory, filename))

    # Create new files
    with app.app_context():
        groups = app.data.driver.db['groups'].find({})
        for g in groups:
            update_group(g, g)  # Use group as update and original


@cli.command()
@config_option
def cron(config):
    """Run scheduled tasks."""
    app = create_app(config_file=config)
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
    app = create_app(config_file=config)
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
    app = create_app(config_file=config, DEBUG=True, TESTING=True)

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
