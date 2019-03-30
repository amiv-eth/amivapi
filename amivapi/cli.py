# -*- coding: utf-8 -*-
#
# license: AGPL, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""A command line interface for AMIVApi."""
from os import listdir, remove
from os.path import join, isdir
from datetime import datetime as dt
from time import sleep

from click import argument, echo, group, option, Path, Choice, ClickException

from amivapi.bootstrap import create_app
from amivapi.cron import run_scheduled_tasks
from amivapi import ldap
from amivapi.groups.mailing_lists import updated_group

try:
    import bjoern
except ImportError:
    bjoern = False


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
            updated_group(g, g)  # Use group as update and original


def run_cron(app):
    """Run scheduled tasks with the given app."""
    echo("Executing scheduled tasks...")
    with app.app_context():
        run_scheduled_tasks()


@cli.command()
@config_option
@option("--continuous", is_flag=True,
        help="If set, continue running in a loop.")
def cron(config, continuous):
    """Run scheduled tasks.

    Use --continuous to keep running and execute tasks periodically.
    """
    app = create_app(config_file=config)

    if not continuous:
        run_cron(app)
    else:
        interval = app.config['CRON_INTERVAL']

        echo('Running scheduled tasks periodically (every %i seconds).'
             % interval.total_seconds())

        while True:
            checkpoint = dt.utcnow()
            run_cron(app)
            execution_time = dt.utcnow() - checkpoint
            echo('Tasks executed, total execution time: %.3f seconds.'
                 % execution_time.total_seconds())

            if execution_time > interval:
                echo('Warning: Execution time exceeds interval length.')

            sleep((interval - execution_time).total_seconds())


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
    if not app.config['ldap_connector']:
        echo("LDAP is not enabled, can't proceed!")
    else:
        with app.test_request_context():
            if sync_all:
                res = ldap.sync_all()
                echo("Synchronized %i users." % len(res))
            else:
                for user in nethz:
                    if ldap.sync_one(user) is not None:
                        echo("Successfully synchronized '%s'." % user)
                    else:
                        echo("Could not synchronize '%s'." % user)


@cli.command()
@config_option
@argument('mode', type=Choice(['prod', 'dev']))
def run(config, mode):
    """Run production/development server.

    Two modes of operation are available:

    - dev: Run a development server

    - prod: Run a production server (requires the `bjoern` module)
    """
    if mode == 'dev':
        app = create_app(config_file=config,
                         ENV='development',
                         DEBUG=True,
                         TESTING=True)
        app.run(threaded=True)

    elif mode == 'prod':
        if bjoern:
            echo('Starting bjoern on port 8080...')
            bjoern.run(create_app(config_file=config), '0.0.0.0', 8080)
        else:
            raise ClickException('The production server requires `bjoern`, '
                                 'try installing it with '
                                 '`pip install bjoern`.')
