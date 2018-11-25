# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Add additional documentation to the Eve-Swagger output.

Eve-Swagger provides a useful baseline, but is missing many details.

Furthermore, as of this commit, development seems slow with multiple open pull
requests without responses. Thus we have decided to update the documentation
manually. Should Eve-Swagger development gain traction again, we could try to
integrate these changes.
"""
from os import path

from eve_swagger import add_documentation


def update_documentation(app):
    """Update the API documentation provided by Eve-Swagger.

    1. Update top-level descriptions etc.
    2. Add definitions for responses and parameters
    3. Update each resource, i.e. lookups, methods, and properties
    """
    _update_top_level(app)
    _update_definitions(app)

    for resource, domain in app.config['DOMAIN'].items():
        _update_properties(domain)
        _update_paths(resource, domain)
        _update_methods(resource, domain)


def _update_top_level(app):
    """Update top-level descriptions."""
    # Extend documentation description
    # Markdown files that will be included in the API documentation
    doc_files = ['Introduction.md', 'Cheatsheet.md', 'Auth.md', 'OAuth.md']
    dirname = path.dirname(path.realpath(__file__))
    doc_paths = [path.join(dirname, filename) for filename in doc_files]

    additional_docs = []
    for filename in doc_paths:
        with open(filename) as file:
            additional_docs.append(file.read().strip())

    # Join parts with double newlines (empty line) for markdown formatting
    docs = app.config['SWAGGER_INFO']
    docs['description'] = "\n\n".join((docs['description'].strip(),
                                       *additional_docs))

    # Add logo
    add_documentation({'info': {'x-logo': app.config['SWAGGER_LOGO']}})

    # Add servers
    add_documentation({'servers': app.config['SWAGGER_SERVERS']})

    # Required to tell online docs that we don't return xml
    app.config['XML'] = False


def _update_definitions(app):
    """Update the definitions in the docs.

    In particular, extend the `parameters` section with definitions
    for the various query parameters, e.g. filter and embed.

    Furthermore, add definitions for the error responses to the `definitions`
    section.
    """
    add_documentation({
        # Query parameters
        'parameters': {
            'auth': {
                "in": "header",
                "name": "Authorization",
                "description": "API token.<br />(read more in "
                               "[Authentication and Authorization]"
                               "(#section/Authentication-and-Authorization))",
                "required": True,
                "type": "string"
            },
            'filter': {
                "in": "query",
                "name": "where",
                "type": "object",
                "description": "Apply a filter."
                               "<br />[(Cheatsheet)](#section/Cheatsheet)",
            },
            'max_results': {
                "in": "query",
                "name": "max_results",
                "type": "integer",
                "minimum": 0,
                "maximum": app.config['PAGINATION_LIMIT'],
                "default": app.config['PAGINATION_DEFAULT'],
                "description": "Limit the number of results per page."
                               "<br />[(Cheatsheet)](#section/Cheatsheet)",
            },
            'page': {
                "in": "query",
                "name": "page",
                "type": "integer",
                "minimum": 1,
                "description": "Specify result page."
                               "<br />[(Cheatsheet)](#section/Cheatsheet)",
            },
            'sort': {
                "in": "query",
                "name": "sort",
                "type": "object",
                "description": "Sort results."
                               "<br />[(Cheatsheet)](#section/Cheatsheet)",
            },
            'embed': {
                "in": "query",
                "name": "embedded",
                "type": "object",
                "description": "Control embedding of related resources."
                               "<br />[(Cheatsheet)](#section/Cheatsheet)",
            },
            'project': {
                "in": "query",
                "name": "projection",
                "type": "object",
                "description": "Show/hide fields in response."
                               "<br />[(Cheatsheet)](#section/Cheatsheet)",
            },
        },

        # Error Responses
        'definitions': {
            '404': {
                'description': 'No item with the provided `_id` exists',
            },
            '401': {
                'description': 'The `Authorization` header is missing or '
                               'contains an invalid token',
            },
            '403': {
                'description': 'The `Authorization` header contains a valid '
                               'token, but you do not have the required '
                               'permissions',
            },
            '422': {
                'description': 'Validation of the document body failed',
            },
            '428': {
                'description': "The `If-Match` header is missing",
            },
            '412': {
                'description': "The `If-Match` header does not match the "
                               "current `_etag`",
            }
        }
    })


def _add_param_refs(path, method, references):
    """Helper to add references to query parameters to a path method."""
    parameters = [{'$ref': '#/parameters/%s' % ref}
                  for ref in references]
    add_documentation({
        'paths': {path: {method.lower(): {'parameters': parameters}}},
    })


def _add_error_refs(path, method, codes):
    """Helper to add references to error responses to a path method."""
    errors = {str(code): {'$ref': '#/definitions/%s' % code}
              for code in codes}

    add_documentation({
        'paths': {path: {method.lower(): {'responses': errors}}},
    })


def _update_properties(domain):
    """Update field properties.

    - Properties can have a title. Use `title` if specified, otherwise
      capitalized field name (without underscores) as default.
    - ReDoc can mark fields as `Nullable` (x-nullable extension).
    - OpenAPI supports writeonly properties.
    - Fix description and example for field with related resources, which
      are not displayed correctly
    """
    def _update_property(prop, key, value):
        """Helper to update a property."""
        add_documentation({'definitions': {
            domain['item_title']: {'properties': {prop: {key: value}}}
        }})

    for prop, prop_def in domain['schema'].items():
        if prop_def.get('nullable'):
            _update_property(prop, 'x-nullable', True)

        if prop_def.get('writeonly'):
            _update_property(prop, 'writeOnly', True)

        default_title = prop.title().replace('_', ' ')
        _update_property(prop, 'title', prop_def.get('title', default_title))

        if 'data_relation' in prop_def:
            for fix in ('description', 'example'):
                _update_property(prop, fix, prop_def.get(fix, ''))

            # Contraty to description and example, the default is optional
            if 'default' in prop_def:
                _update_property(prop, 'default', prop_def['default'])


def _update_paths(resource, domain):
    """Update the lookup paths for a resource.

    Re-format the default _id lookup and add additional lookups,
    if any exist.
    """
    title = domain['item_title']
    key = '%s__id' % title
    path = '/%s/{%sId}' % (resource, title.lower())

    updates = {'description': 'The `_id` field of a %s document' % title}
    add_documentation({'parameters': {key: updates}})

    try:
        lookup = domain['additional_lookup']
    except KeyError:
        pass
    else:
        field = lookup['field']
        params = [{
            'in': 'path',
            'name': field,
            'required': False,
            'description': '*Instead* of the `_id`, you can also use the '
                           '`%s` field as an alternative lookup when '
                           '*retrieving* a document.' % field,
            'type': lookup['url'],
        }]
        add_documentation({
            'paths': {path: {'get': {'parameters': params}}},
        })


def _update_methods(resource, domain):
    """For each method, add the appropriate query params and responses."""
    # 0: Check if the resource has data relation and can use `embedded`
    has_data_relation = any('data_relation' in field_def
                            for field_def in domain['schema'].values())

    # 1: Resource methods, `GET` and `POST` possible
    resource_path = '/%s' % resource
    for method in domain['resource_methods']:
        parameters = []
        errors = []

        if method not in domain['public_methods']:
            errors += [401, 403]
            parameters.append('auth')

        if method == 'GET':
            parameters += ['filter', 'max_results', 'page', 'sort']

        if method == 'POST':
            errors.append(422)

        parameters.append('project')
        if has_data_relation:
            parameters.append('embed')

        _add_error_refs(resource_path, method, errors)
        _add_param_refs(resource_path, method, parameters)

    # 2: Item methods, `GET`, `PATCH` and `DELETE` possible
    item_path = '/%s/{%sId}' % (resource, domain['item_title'].lower())
    for method in domain['item_methods']:
        parameters = []
        errors = [404]  # all item methods can result in 404 if item is missing

        if method not in domain['public_item_methods']:
            errors += [401, 403]
            parameters.append('auth')

        if method == 'GET':
            parameters.append('filter')

        if method == 'PATCH':
            errors += [412, 422, 428]

        if method in ['GET', 'PATCH']:
            parameters.append('project')
            if has_data_relation:
                parameters.append('embed')

        if method == 'DELETE':
            errors += [412, 428]

        _add_error_refs(item_path, method, errors)
        _add_param_refs(item_path, method, parameters)
