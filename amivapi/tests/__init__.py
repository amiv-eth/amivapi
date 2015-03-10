import warnings

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from amivapi import bootstrap, models, utils


engine = None
connection = None


def setup():
    global engine, connection
    warnings.filterwarnings('error', module=r'^sqlalchemy')

    config = bootstrap.get_config("testing")
    engine = create_engine(config['SQLALCHEMY_DATABASE_URI'])
    connection = engine.connect()

    utils.init_database(connection, config)


def teardown():
    """Drop database created above"""
    models.Base.metadata.drop_all(connection)
    connection.close()
