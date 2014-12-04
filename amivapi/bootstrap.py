from os.path import abspath, dirname, join
import codecs
import rsa

from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.config import Config
from flask.ext.bootstrap import Bootstrap
from flask import g

from amivapi import models, confirm, schemas, event_hooks, auth


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


def create_app(environment, create_db=False):
    config = get_config(environment)
    app = Eve(settings=config, data=SQL, validator=ValidatorSQL, auth=auth.TokenAuth)

    # Bind SQLAlchemy
    db = app.data.driver
    models.Base.metadata.bind = db.engine
    db.Model = models.Base
    if create_db:
        db.create_all()

    # Generate and expose docs via eve-docs extension
    Bootstrap(app)
    with app.app_context():
        g.db = db.session
    app.register_blueprint(eve_docs, url_prefix="/docs")
    app.register_blueprint(confirm.confirmprint)

    # Add event hooks
    app.on_pre_GET_users += event_hooks.pre_users_get_callback
    app.on_post_GET_users += event_hooks.post_users_get_callback
    app.on_pre_POST_eventsignups += event_hooks.pre_signups_post_callback
    app.on_insert_eventsignups += event_hooks.preSignupsInsertCallback
    app.on_post_POST_eventsignups += event_hooks.post_signups_post_callback
    app.on_pre_POST_groupmemberships += event_hooks.\
        pre_groupmemberships_post_callback

    app.register_blueprint(auth.auth)

    app.on_insert_users += auth.hash_password_before_insert
    app.on_replace_users += auth.hash_password_before_replace
    app.on_update_users += auth.hash_password_before_update

    return app
