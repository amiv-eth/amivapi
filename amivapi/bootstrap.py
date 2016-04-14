# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
Starting point for the API
"""

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.engine import reflection
from sqlalchemy.schema import (
    MetaData,
    Table,
    DropTable,
    ForeignKeyConstraint,
    DropConstraint,
)

from eve import Eve
from eve_sqlalchemy import SQL  # , ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap
from flask import g

from amivapi import (
    models,
    events,
    schemas,
    authentication,
    authorization,
    media,
    mailing_lists,
    validation,
    ldap,
    documentation,
    group_permissions
)

from amivapi.utils import get_config


def create_app(disable_auth=False, **kwargs):
    """
    Create a new eve app object and initialize everything.

    :param disable_auth: This can be used to allow every request without
                         authentication for testing purposes
    :param **kwargs: All other parameters overwrite config values
    :returns: eve.Eve object, the app object
    """
    config = get_config()
    config['DOMAIN'] = schemas.get_domain()
    config['BLUEPRINT_DOCUMENTATION'] = documentation.get_blueprint_doc()
    config.update(kwargs)

    if disable_auth:
        app = Eve(settings=config,
                  data=SQL,
                  validator=validation.ValidatorAMIV,
                  media=media.FileSystemStorage)
    else:
        app = Eve(settings=config,
                  data=SQL,
                  validator=validation.ValidatorAMIV,
                  auth=authentication.TokenAuth,
                  media=media.FileSystemStorage)

    # Bind SQLAlchemy
    db = app.data.driver
    models.Base.metadata.bind = db.engine
    db.Model = models.Base

    Bootstrap(app)
    with app.app_context():
        g.db = db.session

    # Create LDAP connector
    if config['ENABLE_LDAP']:
        app.ldap_connector = ldap.LdapConnector(config['LDAP_USER'],
                                                config['LDAP_PASS'])

    # Generate and expose docs via eve-docs extension
    app.register_blueprint(eve_docs, url_prefix="/docs")
    app.register_blueprint(authentication.authentication)
    app.register_blueprint(media.download)

    #
    # Event hooks
    #
    # security note: hooks which are run before auth hooks should never change
    # the database
    #

    # authentication
    app.on_insert += authentication.set_author_on_insert
    app.on_replace += authentication.set_author_on_replace

    # authorization
    app.on_pre_GET += authorization.pre_get_permission_filter
    app.on_pre_POST += authorization.pre_post_permission_filter
    app.on_pre_PUT += authorization.pre_put_permission_filter
    app.on_pre_DELETE += authorization.pre_delete_permission_filter
    app.on_pre_PATCH += authorization.pre_patch_permission_filter
    app.on_pre_GET_groups += authorization.group_visibility_filter

    # Hooks for anonymous users
    app.on_insert_eventsignups += events.signups_confirm_anonymous

    app.on_update += events.pre_update_confirmation
    app.on_delete_item += events.pre_delete_confirmation
    app.on_replace += events.pre_replace_confirmation

    # users
    app.on_pre_GET_users += authorization.pre_users_get

    # email-management
    # Addresses
    app.on_inserted_groupaddresses += mailing_lists.create_files
    app.on_replaced_groupaddresses += mailing_lists.update_file
    app.on_updated_groupaddresses += mailing_lists.update_file
    app.on_deleted_item_groupaddresses += mailing_lists.delete_file
    # Members - can not be updated or replaced
    app.on_inserted_groupmembers += mailing_lists.add_user_email
    app.on_deleted_item_groupmembers += mailing_lists.remove_user_email
    # Forwards
    app.on_inserted_groupforwards += mailing_lists.add_forward_email
    app.on_replaced_groupforwards += mailing_lists.replace_forward_email
    app.on_updated_groupforwards += mailing_lists.update_forward_email
    app.on_deleted_item_groupforwards += mailing_lists.remove_forward_email

    # Init modules
    events.init_app(app)

    return app


def init_database(connection, config):
    """Create tables and fill with initial anonymous and root user

    Throws sqlalchemy.exc.OperationalError(sqlite) or
    sqlalchemy.exc.ProgrammingError(mysql) if tables already exist

    :param connection: A database connection
    :param config: The configuration dictionary
    """
    # Tell MySQL to not treat 0 as NULL
    if connection.engine.dialect.name == "mysql":
        connection.execute("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO'")

    try:
        models.Base.metadata.create_all(connection, checkfirst=False)
    except (OperationalError, ProgrammingError):
        print("Creating tables failed. Make sure the database does not exist" +
              " already!")
        raise

    root_user = models.User(
        id=0,
        _author=None,
        _etag='d34db33f',  # We need some etag, not important what it is
        password=u"root",
        firstname=u"Lord",
        lastname=u"Root",
        gender="male",
        email=config['ROOT_MAIL'],
        membership="none"
    )
    anonymous_user = models.User(
        id=-1,
        _author=root_user.id,
        _etag='4l3x15F4G',
        password=u"",
        firstname=u"Anon",
        lastname=u"X",
        gender="male",
        email=u"nobody@example.com",
        membership="none"
    )

    session = Session(bind=connection)
    session.add_all([root_user, anonymous_user])
    session.commit()


def clear_database(engine):
    """ Clears all the tables from the database
    To do this first all ForeignKey constraints are removed,
    then all tables are dropped.

    Code is from
    https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/DropEverything

    :param engine: SQLalchemy engine to use
    """

    conn = engine.connect()

    # the transaction only applies if the DB supports
    # transactional DDL, i.e. Postgresql, MS SQL Server
    trans = conn.begin()

    inspector = reflection.Inspector.from_engine(engine)

    # gather all data first before dropping anything.
    # some DBs lock after things have been dropped in
    # a transaction.

    metadata = MetaData()

    tbs = []
    all_fks = []

    for table_name in inspector.get_table_names():
        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            if not fk['name']:
                continue
            fks.append(
                ForeignKeyConstraint((), (), name=fk['name'])
            )
        t = Table(table_name, metadata, *fks)
        tbs.append(t)
        all_fks.extend(fks)

    for fkc in all_fks:
        conn.execute(DropConstraint(fkc))

    for table in tbs:
        conn.execute(DropTable(table))

    trans.commit()
