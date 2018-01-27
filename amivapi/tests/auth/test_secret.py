"""Test creation of secret key."""

from mock import patch

from amivapi.tests.utils import WebTestNoAuth
from amivapi.auth.utils import init_secret

# Flask requires the config entry to be called 'TOKEN_SECRET'
SECRET_KEY = 'TOKEN_SECRET'


class SecretTest(WebTestNoAuth):
    """Secret key generation test class. Manually call setup as needed."""

    def setUp(self):
        """Skip the normal api setup."""

    def test_no_secret(self):
        """Without init_key, no secret key is in config or db."""
        # Replace init_secret with a dummy function, which does nothing
        with patch('amivapi.auth.init_secret'):
            # Now call setup -- no secret will be initialized
            super(SecretTest, self).setUp()

        self.assertNotIn(SECRET_KEY, self.app.config)

        with self.app.app_context():
            db_item = self.db['config'].find_one({
                SECRET_KEY: {'$exists': True}
            })

        self.assertIsNone(db_item)

    def test_create_secret(self):
        """Test that init_secret creates a secret token & adds it to the db."""
        super(SecretTest, self).setUp()

        with self.app.app_context():
            config_value = self.app.config.get(SECRET_KEY)
            db_item = self.db['config'].find_one({
                SECRET_KEY: {'$exists': True, '$nin': [None, '']}
            })

        self.assertIsNotNone(config_value)
        self.assertIsNotNone(db_item)
        self.assertEqual(config_value, db_item[SECRET_KEY])

    def test_existing_key(self):
        """Test that a secret from the database is used automatically."""
        super(SecretTest, self).setUp()
        new_key = 'Trololololo'
        # Overwrite the key in the database
        with self.app.app_context():
            self.db['config'].update_one(
                {SECRET_KEY: {'$exists': True}},
                {'$set': {SECRET_KEY: new_key}},
            )

            # init_secret loads secret token from db, if it exists
            init_secret(self.app)
            self.assertEqual(self.app.config[SECRET_KEY], new_key)
