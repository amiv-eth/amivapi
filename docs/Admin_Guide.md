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

manage.py offers two functions to trigger ldap imports.

If you want to import new users to the api, enter

    python manage.py ldap_import -n=500

Where -n=500 specifies the max. number of imports. You can of course change this or omit it entirely (in this case the default value will be loaded from the config)

If you want to update users in the database, enter

    python manage.py ldap_update -n=100

Where again the -n option can be used to ignore the config values.
