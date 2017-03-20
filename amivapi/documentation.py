# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Eve Swagger initialization."""

from eve_swagger import add_documentation, swagger
from flask import Blueprint, render_template_string

from amivapi.utils import register_validator

redoc = Blueprint('redoc', __name__, static_url_path='/docs')


@redoc.route('/docs')
def index():
    """Output simple html that includes ReDoc's JS and sets style"""
    redoc_template = (
        '<!DOCTYPE html>'
        '<html><head>'
        '<title>ReDoc</title>'
        '<!-- needed for adaptive design -->'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<!-- ReDoc doesn't change outer page styles -->"
        '<style> body {margin: 0; padding: 0; } </style>'
        '</head>'
        '<body>'
        "<redoc spec-url='{{ request.url }}/api-docs'></redoc>"
        '<script src="https://rebilly.github.io/ReDoc/releases/latest/'
        'redoc.min.js"> </script>'
        '</body></html>')
    return render_template_string(redoc_template)


class DocValidator(object):
    """Add a schema rule for a 'descriptions field'.

    This rule will do nothing, but will stop Cerberus from complaining without
    allowing all unknown fields.
    """

    def _validate_description(*args):
        """Do nothing."""


def init_app(app):
    """Create a ReDoc endpoint at /docs."""
    # Generate documentation (i.e. swagger/OpenApi) to be used by any UI
    # will be exposed at /docs/api-docs
    app.register_blueprint(swagger, url_prefix="/docs")
    # host the ui (we use redoc) at /docs
    app.register_blueprint(redoc)

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

    # just an example of how to include code samples
    add_documentation({'paths': {'/sessions': {'post': {
        'x-code-samples': [
            {'lang': 'python',
             'source': '\n\n'.join([
                'import requests',
                ('login = requests.post("http://api.amiv.ethz.ch/sessions", '
                 'data={"user": "myuser", "password": "mypassword"})'),
                "token = login.json()['token']",
                ('# now use this token to authenticate a request\n'
                 'response = requests.get('
                 '"https://api.amiv.ethz.ch/users/myuser", '
                 'auth=requests.auth.HTTPBasicAuth(token, ""))')])
             }
        ]
    }}}})
