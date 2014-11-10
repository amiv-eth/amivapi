import warnings

from sqlalchemy import create_engine

from amivapi import bootstrap, models


engine = None
connection = None


def setup():
    global engine, connection
    warnings.filterwarnings('error', module=r'^sqlalchemy')

    config = bootstrap.get_config("testing")
    engine = create_engine(config['SQLALCHEMY_DATABASE_URI'])
    connection = engine.connect()

    models.Base.metadata.create_all(connection, checkfirst=False)


def teardown():
    """Drop database created above"""
    models.Base.metadata.drop_all(connection)
    connection.close()
