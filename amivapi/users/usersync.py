# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Provide an endpoint to sync users as if they logged in on the Website."""
from flask import abort, request, Blueprint, g, jsonify

from amivapi import ldap
from amivapi.auth import authenticate
from amivapi.groups import check_group_permissions


blueprint = Blueprint('user_sync', __name__)


@blueprint.route('/usersync', methods=['POST'])
def usersync():
    """Sync user with LDAP as if they logged in.

    Runs the ldap sync if the user has readwrite
    permission on the users resource

    request body:
    `{"nethz": "hmuster"}`
    """

    authenticate()
    check_group_permissions('users')

    if g.get('resource_admin'):
        nethz = request.json.get('nethz')
        if nethz:
            res = ldap.sync_one(nethz)
            return jsonify(res)
        abort(422)
    abort(401)


def init_user_sync(app):
    """Register the user_sync blueprint."""
    app.register_blueprint(blueprint)
