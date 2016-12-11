# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Eve Swagger initialization."""

from flask import Blueprint, redirect, url_for, request

from eve_swagger import swagger, add_documentation

from amivapi.utils import register_validator

swagger_ui = Blueprint('swagger_ui', __name__,
                       static_folder='swagger_ui',
                       static_url_path='/docs')


@swagger_ui.route('/docs')
def index():
    """Redirect to the correct url to view docs."""
    return redirect(url_for('swagger_ui.static', filename='index.html') +
                    "?url={}/api-docs".format(request.url))


class DocValidator(object):
    """Add a schema rule for a 'descriptions field'.

    This rule will do nothing, but will stop Cerberus from complaining without
    allowing all unknown fields.
    """

    def _validate_description(*args):
        """Do nothing."""


def init_app(app):
    """Create a swagger-ui endpoint at /docs."""
    # Generate documentation to be used by swagger ui
    # will be exposed at /api-docs
    app.register_blueprint(swagger, url_prefix="/docs")
    # host the swagger ui at /docs

    app.register_blueprint(swagger_ui)

    register_validator(app, DocValidator)

    # replace null-type fields with ''
    # TODO: make this dynamic
    add_documentation({'definitions': {'User': {'properties': {
        'password': {'default': ''},
        'nethz': {'default': ''}
    }}}})

    add_documentation({'securityDefinitions': {
        'AMIVauth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter a session token you got with POST to '
            '/sessions, or an API key, stored in the server config'
        }
    }})
