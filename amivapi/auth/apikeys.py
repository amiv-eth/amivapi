# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

""" Hook to allow authorization with apikeys """

from flask import current_app, request, abort, g

from ruamel import yaml


def authorize_apikeys(resource):
    """ Check if user is an apikey, and if it is, do authorization """
    if (g.get('current_token') and
            g.current_token in current_app.config['APIKEYS']):
        perms = current_app.config['APIKEYS'][g.current_token]['PERMISSIONS']

        if request.method in perms.get(resource, []):
            g.resource_admin = True
        else:
            # If an API key is used, deny everything else, even public things
            abort(403, "Your API key does not grant access to the requested"
                  "endpoint.")


def init_apikeys(app):
    """ Load apikeys from config file and add auth hook """
    # Load apikeys
    try:
        with open(app.config['APIKEY_FILENAME'], 'r') as f:
            yaml_data = yaml.load(f)
            app.config['APIKEYS'] = yaml_data
    except IOError:
        app.config['APIKEYS'] = {}

    # Add auth hook
    app.after_auth += authorize_apikeys
