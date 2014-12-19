"""Default settings for all environments.

These settings will be extended by additional config files in ROOT/config.
Run `python manage.py create_config` to create such a config file.
"""

from os.path import abspath, dirname, join

# Custom
ROOT_DIR = abspath(join(dirname(__file__), ".."))

# Flask
DEBUG = False
TESTING = False

# Flask-SQLALchemy

# Eve
ID_FIELD = "id"
AUTH_FIELD = "_author"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
BANDWIDTH_SAVER = False
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']
PUBLIC_METHODS = ['GET']  # This is the only way to make / public
XML = False

# Eve, file storage options
RETURN_MEDIA_AS_BASE64_STRING = False
EXTENDED_MEDIA_INFO = ['filename', 'size', 'content_url']
STORAGE_URL = r'/storage'
