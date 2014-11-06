from os.path import abspath, dirname, join

from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap

from amivapi import schema, models

ROOT_PATH = abspath(join(dirname(__file__), ".."))

eve_settings = {
    'DOMAIN': schema.RESOURCES,
    'DATE_FORMAT': "%Y-%m-%dT%H:%M:%SZ",
    'RESOURCE_METHODS': ['GET', 'POST'],
    'ITEM_METHODS': ['GET', 'PATCH', 'PUT', 'DELETE'],

    'BANDWIDTH_SAVER': False,
    'XML': False,

    'SQLALCHEMY_DATABASE_URI': "sqlite:///%s/data.db" % ROOT_PATH,
    'SQLALCHEMY_ECHO': True,
}

app = Eve(settings=eve_settings, data=SQL, validator=ValidatorSQL)

# Bind SQLAlchemy
db = app.data.driver
models.Base.metadata.bind = db.engine
db.Model = models.Base
db.create_all()

# Generate and expose docs via eve-docs extension
Bootstrap(app)
app.register_blueprint(eve_docs, url_prefix="/docs")


if __name__ == '__main__':
    app.run(debug=True)
