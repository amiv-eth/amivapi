# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Hook to allow authorization with apikeys."""

from flask import abort, current_app, g

from ruamel import yaml


def authorize_apikeys(resource):
    """Check if user is an apikey, and if it is, do authorization."""
    permissions = [
        data['permissions'] for data in current_app.config['APIKEYS'].values()
        if data['token'] == g.get('current_token')]
    if permissions:
        # We can just take first (and only) element since token is unique
        permission = permissions[0].get(resource)

        if permission == 'read':
            g.resource_admin_readonly = True
        elif permission == 'readwrite':
            g.resource_admin = True
        elif g.get('auth_required'):
            abort(403, "The APIKEY does not grant the required permissions.")


def init_apikeys(app):
    """Load apikeys from config file and add auth hook."""
    try:
        with open(app.config['APIKEY_FILENAME'], 'r') as f:
            data = yaml.load(f)
            app.config['APIKEYS'] = data if data is not None else {}
    except IOError:
        app.config['APIKEYS'] = {}

    # Add auth hook
    app.after_auth += authorize_apikeys
