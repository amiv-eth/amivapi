# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Online documentation initialization.

We use ReDoc to display an OpenAPI documentation.
The documenation is produced by Eve-Swagger, which we extend with details.
"""
from flask import Blueprint, render_template_string, current_app
from eve_swagger import swagger


from .update_documentation import update_documentation


redoc = Blueprint('redoc', __name__, static_url_path='/docs')


doc_template = ("""
<!DOCTYPE html>
<html>
  <head>
    <title>{{ title }}</title>

    <!-- Responive Sizing -->
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <!-- Normalize Page Style -->
    <style>body { margin: 0; padding: 0; }</style>
  </head>

  <body>
    <redoc spec-url={{ spec_url }}></redoc>
    <script src=
    "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js">
    </script>
  </body>
</html>
""")


@redoc.route('/docs')
def index():
    """Output simple html that includes ReDoc's JS and sets styles."""
    spec_url = '/docs/api-docs'

    title = current_app.config['SWAGGER_INFO']['title']
    return render_template_string(doc_template,
                                  spec_url=spec_url,
                                  title=title)


def init_app(app):
    """Create a ReDoc endpoint at /docs."""
    # Generate documentation (i.e. swagger/OpenApi) to be used by any UI
    # will be exposed at /docs/api-docs
    app.register_blueprint(swagger, url_prefix="/docs")
    # host the ui (we use redoc) at /docs
    app.register_blueprint(redoc)

    update_documentation(app)
