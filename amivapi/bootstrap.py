from os.path import abspath, dirname, join

from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.config import Config
from flask.ext.bootstrap import Bootstrap

from amivapi import models


def get_config(environment):
    config_dir = abspath(join(dirname(__file__), "../config"))
    config = Config(config_dir)
    config.from_object("amivapi.settings")
    try:
        config.from_pyfile("%s.cfg" % environment)
    except IOError as e:
        raise IOError(str(e) + "\nYou can create it by running "
                             + "`python manage.py create_config`.")

    domain = config['DOMAIN'] = {}
    for obj_name in dir(models):
        obj = getattr(models, obj_name)
        if hasattr(obj, "_eve_schema"):
            domain.update(obj._eve_schema)

    return config


def create_app(environment, create_db=False):
    config = get_config(environment)
    app = Eve(settings=config, data=SQL, validator=ValidatorSQL)

    # Bind SQLAlchemy
    db = app.data.driver
    models.Base.metadata.bind = db.engine
    db.Model = models.Base
    if create_db:
        db.create_all()

    # Generate and expose docs via eve-docs extension
    Bootstrap(app)
    app.register_blueprint(eve_docs, url_prefix="/docs")

    return app
