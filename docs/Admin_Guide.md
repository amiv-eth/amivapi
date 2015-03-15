# Admin tasks

# Cron

The API requires a cron job to do tasks on a regular basis, which includes
sending warnings about expiring permissions. You should configure a cronjob to
run `amivapi/cron.py` once per day.
Append something like this to your crontab:

    39 3 * * *   /path/to/env/python /path/to/api/amivapi/cron.py
