# Admin tasks

# Cron

The API requires a cron job do to tasks on a regular basis, which includes
sending warnings about expiring permissions. You should configure a cronjob to
run `manage.py run_cron -c <environment>` once per day.
Append something like this to your crontab:

    39 3 * * *   <path to python>/python <your_api_path>/manage.py run_cron -c production
