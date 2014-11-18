from flask import Blueprint, request
from amivapi.models import GroupMembership, User, Group

import json

logics = Blueprint('logics', __name__)


@logics.route('/groupmemberships', methods=['POST'])
def newGroupMembership():
    data = json.loads(request.data)
    membership = GroupMembership()
    membership.expiry_date = data.get('expiry_date')
    user = db.query(User).get(data.get('user_id'))
    group = db.query(Group).get(data.get('group_id'))
    membership.user = user
    membership.group = group
    db.add(membership)
    db.session.commit()
    return 'Thanks'
