"""Util functions used throughout the Event system."""
from eve import Eve
from flask import current_app as current_app

try:
    from secrets import token_urlsafe
except ImportError:
    # Fallback for python3.5
    from amivapi.utils import token_urlsafe


def create_token_secret_on_startup(app: Eve) -> None:
    """Create a token secret in the database if it doesn't exist.

    The secret key is stored in the database to ensure consistency.
    The database collection holding this key is called `config`.
    """
    with app.app_context():  # Context for db connection
        config = app.data.driver.db['config']
        result = config.find_one(
            {'TOKEN_SECRET': {'$exists': True, '$nin': [None, '']}})

        if result is None:
            config.insert_one({'TOKEN_SECRET': token_urlsafe()})


def get_token_secret() -> str:
    db = current_app.data.driver.db['config']
    result = db.find_one({'TOKEN_SECRET': {'$exists': True}})
    return result['TOKEN_SECRET']
