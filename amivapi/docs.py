from flask import Blueprint, redirect, url_for, request

from eve_swagger import swagger, add_documentation

swagger_ui = Blueprint('swagger_ui', __name__,
                       static_folder='swagger_ui',
                       static_url_path='/docs')


@swagger_ui.route('/docs')
def index():
    return redirect(url_for('swagger_ui.static', filename='index.html')
                    + "?url={}/api-docs".format(request.url))


def init_app(app):
    """Create a swagger-ui endpoint at /docs."""

    # Generate documentation to be used by swagger ui
    # will be exposed at /api-docs
    app.register_blueprint(swagger, url_prefix="/docs")
    # host the swagger ui at /docs

    app.register_blueprint(swagger_ui)

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
            'description': 'enter a token you got with POST to /sessions'
        }
    }})
