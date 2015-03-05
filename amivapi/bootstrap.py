from os.path import abspath, dirname, join

from eve import Eve
from eve_sqlalchemy import SQL  # , ValidatorSQL
from eve_docs import eve_docs
from flask.config import Config
from flask.ext.bootstrap import Bootstrap
from flask import g

from amivapi import \
    models, \
    confirm, \
    schemas, \
    event_hooks, \
    authentification, \
    authorization, \
    file_endpoint, \
    media, \
    forwards

from amivapi.validation import ValidatorAMIV


def get_config(environment):
    config_dir = abspath(join(dirname(__file__), "../config"))
    config = Config(config_dir)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("%s.cfg" % environment)
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                             + "`python manage.py create_config`.")

    schemas.load_domain(config)

    return config


def create_app(environment, disable_auth=False):
    config = get_config(environment)

    if disable_auth:
        app = Eve(settings=config,
                  data=SQL,
                  validator=ValidatorAMIV,
                  media=media.FileSystemStorage)
    else:
        app = Eve(settings=config,
                  data=SQL,
                  validator=ValidatorAMIV,
                  auth=authentification.TokenAuth,
                  media=media.FileSystemStorage)

    # Bind SQLAlchemy
    db = app.data.driver
    models.Base.metadata.bind = db.engine
    db.Model = models.Base

    Bootstrap(app)
    with app.app_context():
        g.db = db.session

    # Generate and expose docs via eve-docs extension
    app.register_blueprint(eve_docs, url_prefix="/docs")
    app.register_blueprint(confirm.confirmprint)
    app.register_blueprint(authentification.authentification)
    app.register_blueprint(authorization.permission_info)
    app.register_blueprint(file_endpoint.download, url_prefix="/storage")

    # Add event hooks
    # security note: hooks which are run before auth hooks should never change
    # the database

    app.on_insert += event_hooks.pre_insert_check
    app.on_update += event_hooks.pre_update_check
    app.on_replace += event_hooks.pre_replace_check

    """eventsignups"""
    """for signups we need extra hooks to confirm the field extra_data"""
    app.on_pre_POST_eventsignups += event_hooks.pre_signups_post
    app.on_pre_PATCH_eventsignups += event_hooks.pre_signups_patch
    app.on_pre_UPDATE_eventsignups += event_hooks.pre_signups_update
    app.on_pre_PUT_eventsignups += event_hooks.pre_signups_put

    """for anonymous users"""
    app.on_post_POST_eventsignups += event_hooks.signups_send_confirmation_mail
    app.on_insert_eventsignups += event_hooks.signups_confirm_anonymous

    """forwardaddresses"""
    app.on_delete_item_forwardaddresses += event_hooks.\
        forwardaddresses_delete_anonymous

    """users"""
    app.on_pre_GET_users += event_hooks.pre_users_get
    app.on_pre_PATCH_users += event_hooks.pre_users_patch

    """authentification"""
    app.on_insert_users += authentification.hash_password_before_insert
    app.on_replace_users += authentification.hash_password_before_replace
    app.on_update_users += authentification.hash_password_before_update

    app.on_insert += event_hooks.set_author_on_insert
    app.on_replace += event_hooks.set_author_on_replace

    if not disable_auth:
        app.on_pre_GET += authorization.pre_get_permission_filter
        app.on_pre_POST += authorization.pre_post_permission_filter
        app.on_pre_PUT += authorization.pre_put_permission_filter
        app.on_pre_DELETE += authorization.pre_delete_permission_filter
        app.on_pre_PATCH += authorization.pre_patch_permission_filter
        app.on_update += authorization.update_permission_filter

    """email-management"""
    app.on_deleted_item_forwards += forwards.on_forward_deleted
    app.on_inserted_forwardusers += forwards.on_forwarduser_inserted
    app.on_replaced_forwardusers += forwards.on_forwarduser_replaced
    app.on_updated_forwardusers += forwards.on_forwarduser_updated
    app.on_deleted_item_forwardusers += forwards.on_forwarduser_deleted
    app.on_inserted_forwardaddresses += forwards.on_forwardaddress_inserted
    app.on_replaced_forwardaddresses += forwards.on_forwardaddress_replaced
    app.on_updated_forwardaddresses += forwards.on_forwardaddress_updated
    app.on_deleted_item_forwardaddresses += forwards.on_forwardaddress_deleted

    # Delete files when studydocument is deleted
    app.on_delete_item_studydocuments += media.delete_study_files

    return app
