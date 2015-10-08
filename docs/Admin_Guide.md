# Admin tasks

# Cron

The API requires a cron job to do tasks on a regular basis, which includes
sending warnings about expiring permissions. You should configure a cronjob to
run `amivapi/cron.py` once per day.
Append something like this to your crontab:

    39 3 * * *   /path/to/env/python /path/to/api/amivapi/cron.py

# Using manage.py

The API offers a convenient management tool for various tasks. This is provided by [flask-script](https://flask-script.readthedocs.org/en/latest/)
and all the functions can be found in manage.py.

The functions can be used with:

    python manage.py somefunction --option=something

A quick guide for the most important functions:

## LDAP

manage.py offers a functions to trigger ldap synchronization.

    python manage.py ldap_sync

This imports all users missing from ldap to the api and updates existing users
