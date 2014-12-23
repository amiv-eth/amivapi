from flask import current_app as app

from amivapi import models


def delete_user_cleanup(item):
    """ Users can not be deleted yet, so this is not important """
    db = app.data.driver.session

    """ Change author of everything created by the user to anonymous """
    # TODO(Conrad): Implement this somehow
    # objs = db.query(models.BaseModel).filter_by(_author=item.id).all()
    # for obj in objs:
    #     obj._author = -1

    """ Delete all permissions """
    objs = db.query(models.Permission).filter_by(user_id=item['id']).all()
    for obj in objs:
        db.delete(obj)

    """ Give mailinglists to root """
    objs = db.query(models.Forward).filter_by(owner_id=item['id']).all()
    for obj in objs:
        obj.owner_id = 0

    """ Remove from forwards """
    objs = db.query(models.ForwardUser).filter_by(user_id=item['id']).all()
    for obj in objs:
        db.delete(obj)

    """ Delete all sessions """
    objs = db.query(models.Session).filter_by(user_id=item['id']).all()
    for obj in objs:
        db.delete(obj)

    """ Remove all signups """
    objs = db.query(models.EventSignup).filter_by(user_id=item['id']).all()
    for obj in objs:
        db.delete(obj)

    db.commit()


def replace_user_cleanup(item, original):
    delete_user_cleanup(item)


def delete_forward_cleanup(item):
    """ Remove all forward entries with the forward """
    objs = models.ForwardUser.query(forward_id=item.id).all()
    for obj in objs:
        app.data.driver.session.delete(obj)

    objs = models.ForwardAddress.query(forward_id=item.id).all()
    for obj in objs:
        app.data.driver.session.delete(obj)

    app.data.driver.session.commit()


def replace_forward_cleanup(item, original):
    delete_forward_cleanup(item)


def delete_event_cleanup(item):
    """ Removes all signups with the event """
    objs = models.EventSignup.query(event_id=item.id).all()
    for obj in objs:
        app.data.driver.session.delete(obj)

    app.data.driver.session.commit()


def replace_event_cleanup(item, original):
    delete_event_cleanup(item)
