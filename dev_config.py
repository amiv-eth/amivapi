import logging

# Mongo config. Do not change!
MONGO_HOST = 'mongodb'
MONGO_PORT = 27017
MONGO_DBNAME = 'amivapi'
MONGO_USERNAME = 'amivapi'
MONGO_PASSWORD = 'amivapi'

# Add other config options as you need below.
ROOT_PASSWORD = 'root'

LOG_LEVEL = logging.DEBUG

# Sentry error logging
# SENTRY_DSN = "https://<key>@sentry.io/<project>"
# SENTRY_ENVIRONMENT = 'production'

# Mailing lists for groups (optional, uncomment if needed)
# MAILING_LIST_DIR = '/directory/to/store/mailing/list/files/'

# Remote mailings list files via ssh (optional)
# REMOTE_MAILING_LIST_ADDRESS = 'user@remote.host'
# REMOTE_MAILING_LIST_KEYFILE = ''
# REMOTE_MAILING_LIST_DIR = './'

# SMTP configuration for mails sent by AMIVAPI (optional)
# SMTP_SERVER = 'localhost'
# SMTP_PORT = '587'
# SMTP_USERNAME = ''
# SMTP_PASSWORD = ''

# Mail configuration (`{subject}` is a placeholder, filled by the API)
# API_MAIL = 'api@amiv.ethz.ch'
# API_MAIL_SUBJECT = '[AMIV] {subject}'

# Allow accessing a list of newsletter subscribers at /newslettersubscribers
# SUBSCRIBER_LIST_USERNAME = ''
# SUBSCRIBER_LIST_PASSWORD = ''

# LDAP connection (special LDAP user required, *not* nethz username & password)
# LDAP_USERNAME = ''
# LDAP_PASSWORD = ''
