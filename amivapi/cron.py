"""
Actions to be done on a regular basis. The run function should be executed
once per day
"""


from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from amivapi.models import Permission, Session
from amivapi.utils import get_config


def delete_expired_sessions(db, config):
    """ Delete expired sessions

    :param db: The db session
    :param config: Config dict
    """
    timeout = config['SESSION_TIMEOUT']

    query = db.query(Session).filter(
        Session._updated <= datetime.now() - timeout)

    for entry in query:
        db.delete(entry)

    db.commit()


def delete_expired_permissions(db, config):
    """ Delete expired permissions and warn users if their permissions will
    expire in 14 days per mail

    :param db: The db session
    :param config: config dict
    """
    # warn people if it will expire in 14 days
    query = db.query(Permission).filter(
        Permission.expiry_date <= datetime.now() + timedelta(days=14),
        Permission.expiry_date >= datetime.now() + timedelta(days=13))

    for entry in query:
        msg = MIMEText(config['PERMISSION_EXPIRED_WARNMAIL_TEXT'] %
                       dict(name=entry.user.firstname, role=entry.role,
                            admin_mail=config['ROOT_MAIL']))
        msg['Subject'] = (
            config['PERMISSION_EXPIRED_WARNMAIL_SUBJECT']
            % dict(role=entry.role))
        msg['From'] = config['ROOT_MAIL']
        msg['To'] = entry.user.email

        try:
            s = smtplib.SMTP(config['SMTP_SERVER'])
            try:
                s.sendmail(msg['From'], [msg['To']], msg.as_string())
            except smtplib.SMTPRecipientsRefused, e:
                print("Failed to send mail to %s about expiring "
                      "permissions: %s" % (entry.user.email, e))
            s.quit()
        except smtplib.SMTPException, e:
            print("Error trying to send mails: %s" % e)

    # delete permissions which are expired

    query = db.query(Permission).filter(
        Permission.expiry_date <= datetime.now())

    for entry in query:
        db.delete(entry)

    db.commit()


def run(db, config):
    """ Run cron tasks

    :param db: The db session
    :param config: The config dict
    """
    delete_expired_permissions(db, config)
    delete_expired_sessions(db, config)


# Run


if __name__ == '__main__':
    cfg = get_config()

    engine = create_engine(cfg['SQLALCHEMY_DATABASE_URI'])
    sessionmak = sessionmaker(bind=engine)
    session = sessionmak()

    run(session, cfg)
