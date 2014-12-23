from os.path import abspath, dirname, join
import codecs
import rsa

from eve import Eve
from eve.io.sql import SQL  # , ValidatorSQL
from eve_docs import eve_docs
from flask.config import Config
from flask.ext.bootstrap import Bootstrap
from flask import g

from amivapi import \
    models, \
    confirm, \
    schemas, \
    event_hooks, \
    auth, \
    download, \
    delete_hooks, \
    media

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

    # Load private key to sign login tokens
    key_file = join(config_dir, "%s-login-private.pem" % environment)
    try:
        config['LOGIN_PRIVATE_KEY'] = rsa.PrivateKey.load_pkcs1(
            codecs.open(key_file, "r", "utf-8").read(),
            format='PEM')
    except IOError as e:
        raise IOError(str(e) + "\nYour private key is missing. Run "
                      + "`python manage.py create_config` to create it!")

    return config


def create_app(environment, disable_auth=False):
    config = get_config(environment)

    if disable_auth:
        app = Eve(settings=config, data=SQL, validator=ValidatorAMIV,
                  media=media.FileSystemStorage)
    else:
        app = Eve(settings=config, data=SQL, validator=ValidatorAMIV,
                  auth=auth.TokenAuth, media=media.FileSystemStorage)

    # Bind SQLAlchemy
    db = app.data.driver
    models.Base.metadata.bind = db.engine
    db.Model = models.Base

    # Generate and expose docs via eve-docs extension
    Bootstrap(app)
    with app.app_context():
        g.db = db.session
    app.register_blueprint(eve_docs, url_prefix="/docs")
    app.register_blueprint(confirm.confirmprint)
    app.register_blueprint(auth.auth)
    app.register_blueprint(download.download, url_prefix="/storage")

    # Add event hooks
    # security note: hooks which are run before auth hooks should never change
    # the database

    app.on_insert += event_hooks.pre_insert_callback
    app.on_update += event_hooks.pre_update_callback

    app.on_pre_POST_eventsignups += event_hooks.pre_signups_post_callback
    app.on_pre_PATCH_eventsignups += event_hooks.pre_signups_patch_callback
    app.on_post_POST_eventsignups += event_hooks.post_signups_post_callback
    app.on_insert_eventsignups += event_hooks.signups_confirm_anonymous

    app.on_insert_forwardaddresses += event_hooks.\
        pre_forwardaddresses_insert_callback
    app.on_post_POST_forwardaddresses += event_hooks.\
        post_forwardaddresses_post_callback
    app.on_pre_PATCH_forwardaddresses += event_hooks.\
        pre_forwardaddresses_patch_callback

    app.on_insert_users += auth.hash_password_before_insert
    app.on_replace_users += auth.hash_password_before_replace
    app.on_update_users += auth.hash_password_before_update

    app.on_insert += auth.set_author_on_insert
    app.on_replace += auth.set_author_on_replace

    app.on_delete_item_users += delete_hooks.delete_user_cleanup
    app.on_delete_item_forwards += delete_hooks.delete_forward_cleanup
    app.on_delete_item_event += delete_hooks.delete_event_cleanup
    app.on_replace_users += delete_hooks.replace_user_cleanup
    app.on_replace_forwards += delete_hooks.replace_forward_cleanup
    app.on_replace_event += delete_hooks.replace_event_cleanup

    if not disable_auth:
        app.on_pre_GET += auth.pre_get_permission_filter
        app.on_pre_POST += auth.pre_post_permission_filter
        app.on_pre_PUT += auth.pre_put_permission_filter
        app.on_pre_DELETE += auth.pre_delete_permission_filter
        app.on_pre_PATCH += auth.pre_patch_permission_filter
        app.on_update += auth.update_permission_filter

    # Delete files when studydocument is deleted
    app.on_delete_item_studydocuments += media.delete_study_files

    return app
