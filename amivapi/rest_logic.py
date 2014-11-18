#from flask import Blueprint, request, g
#from amivapi.models import GroupMembership, User, Group

from flask import Blueprint

logics = Blueprint('logics', __name__)


@logics.route('/groupmemberships', methods=['POST'])
def newGroupMembership():
    """
    data = request.get_json()
    membership = GroupMembership()
    membership.expiry_date = data.get('expiry_date')
    user = g.db.query(User).get(data.get('user_id'))
    group = g.db.query(Group).get(data.get('group_id'))
    membership.user = user
    membership.group = group
    g.db.add(membership)
    g.db.session.commit()
    """
    return 'Thanks'
