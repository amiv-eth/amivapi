# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Eve Swagger initialization."""

from flask import Blueprint, render_template

from eve_swagger import swagger, add_documentation

from amivapi.utils import register_validator

redoc = Blueprint('redoc', __name__, static_url_path='/docs',
                  template_folder='ReDoc')


@redoc.route('/docs')
def index():
    """Redirect to the correct url to view docs."""
    return render_template('index.html')


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
    # will be exposed at /prefix/api-docs
    app.register_blueprint(swagger, url_prefix="/docs")
    # host the swagger ui (we use redoc) at /docs
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
                 'auth=requests.auth.HTTPBasicAuth(token, ""))')
            ])}
        ]}}}})
