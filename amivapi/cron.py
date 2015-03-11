from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

from amivapi.models import Permission, Session

"""
    Actions to be done on a regular basis. The run function should be executed
    once per day
"""


def delete_expired_sessions(db, config):
    timeout = config['SESSION_TIMEOUT']

    query = db.query(Session).\
        filter(Session._updated <= datetime.now() - timeout)

    for entry in query:
        db.delete(entry)

    db.commit()


def delete_expired_permissions(db, config):
    # warn people if it will expire in 14 days

    query = db.query(Permission).\
        filter(Permission.expiry_date <= datetime.now() + timedelta(days=14),
               Permission.expiry_date >= datetime.now() + timedelta(days=13))

    for entry in query:
        msg = MIMEText(config['PERMISSION_EXPIRED_WARNMAIL_TEXT'] %
                       (entry.user.firstname, entry.role, config['ROOT_MAIL']))
        msg['Subject'] =\
            config['PERMISSION_EXPIRED_WARNMAIL_SUBJECT'] % entry.role
        msg['From'] = config['ROOT_MAIL']
        msg['To'] = entry.user.email

        try:
            s = smtplib.SMTP(config['SMTP_SERVER'])
            try:
                s.sendmail(msg['From'], [msg['To']], msg.as_string())
            except smtplib.SMTPRecipientsRefused, e:
                print("Failed to send mail to %s " % entry.user.email +
                      "about expiring permissions: %s" % e)
            s.quit()
        except smtplib.SMTPException, e:
            print("Error trying to send mails: %s" % e)

    # delete permissions which are expired

    query = db.query(Permission).\
        filter(Permission.expiry_date <= datetime.now())

    for entry in query:
        db.delete(entry)

    db.commit()


"""
    Run cron tasks, this is called by manage.py
"""


def run(db, config):
    delete_expired_permissions(db, config)
    delete_expired_sessions(db, config)
