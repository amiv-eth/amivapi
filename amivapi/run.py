from eve import Eve
from eve.io.sql import SQL, ValidatorSQL
from eve_docs import eve_docs
from flask.ext.bootstrap import Bootstrap

from amivapi import schema, models, config


eve_settings = {
    'DOMAIN': schema.RESOURCES,
    'DATE_FORMAT': config.DATE_FORMAT,
    'RESOURCE_METHODS': ['GET', 'POST'],
    'ITEM_METHODS': ['GET', 'PATCH', 'PUT', 'DELETE'],

    'BANDWIDTH_SAVER': config.BANDWIDTH_SAVER,
    'XML': config.XML,

    'SQLALCHEMY_DATABASE_URI': config.SQLALCHEMY_DATABASE_URI,
    'SQLALCHEMY_ECHO': config.SQLALCHEMY_ECHO,
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
