"""Test creation of secret key."""

from mock import patch

from amivapi.tests.utils import WebTestNoAuth
from amivapi.events.utils import (
    create_token_secret_on_startup,
    get_token_secret
)

SECRET_KEY = 'TOKEN_SECRET'


class SecretTest(WebTestNoAuth):
    """Secret key generation test class. Manually call setup as needed."""

    def setUp(self):
        """Skip the normal api setup."""

    def test_no_secret(self):
        """Without init_key, no secret key is in db."""
        # Replace init_secret with a dummy function, which does nothing
        with patch('amivapi.events.create_token_secret_on_startup'):
            # Now call setup -- no secret will be initialized
            super(SecretTest, self).setUp()

        with self.app.app_context():
            db_item = self.db['config'].find_one({
                SECRET_KEY: {'$exists': True}
            })

        self.assertIsNone(db_item)

    def test_create_secret(self):
        """Test that init_secret creates a secret token & adds it to the db."""
        super(SecretTest, self).setUp()

        with self.app.app_context():
            db_item = self.db['config'].find_one({
                SECRET_KEY: {'$exists': True, '$nin': [None, '']}
            })

        self.assertIsNotNone(db_item)

    def test_existing_secret(self):
        """Test that a secret from the database is not overwritten."""
        # We need to run the setup to be able to use an app context
        super(SecretTest, self).setUp()

        old_secret = 'Trololololo'
        # Set the secret in the database
        with self.app.app_context():
            self.db['config'].update_one(
                {SECRET_KEY: {'$exists': True}},
                {'$set': {SECRET_KEY: old_secret}}
            )

        # This should now not change the token
        create_token_secret_on_startup(self.app)

        with self.app.app_context():
            self.assertEqual(get_token_secret(), old_secret)
