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


def update_documentation(app,swagger):
    """Update the API documentation provided by Eve-Swagger.

    1. Update top-level descriptions etc.
    2. Add definitions for responses and parameters
    3. Update each resource, i.e. lookups, methods, and properties
    """
    _update_top_level(app, swagger)
    _update_definitions(app, swagger)

    for resource, domain in app.config['DOMAIN'].items():
        print('****')
        print(resource)
        print('----')
        print(domain)
        print('****')
        _update_properties(swagger, domain)
        _update_paths(swagger, resource, domain)
        _update_methods(swagger, resource, domain)


def _update_top_level(app, swagger):
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
    add_documentation(swagger, {'info': {'x-logo': app.config['SWAGGER_LOGO']}})

    # Add servers
    add_documentation(swagger, {'servers': app.config['SWAGGER_SERVERS']})

    # Required to tell online docs that we don't return xml
    app.config['XML'] = False


def _create_error_message(code, description, additional_properties={}):
    """Creates the schema for an error message."""

    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        **additional_properties,
                        "_status": {"type": "string", "const": "ERR"},
                        "_error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "integer", "const": code },
                                "message": {"type": "string"},
                            },
                        },
                    },
                    "required": ["_status", "_error", [*additional_properties]],
                }
            }
        }
    }

def _update_definitions(app, swagger):
    """Update the definitions in the docs.

    In particular, extend or override existing items in the `parameters`
    section with definitions for the various query parameters, e.g. query__where
    and embed.

    Furthermore, add definitions for the error responses to the `definitions`
    section.
    """
    add_documentation(swagger, {
        'components': {
            # Query parameters
            'parameters': {
                'auth': {
                    "in": "header",
                    "name": "Authorization",
                    "description": "API token.<br />(read more in "
                                "[Authentication and Authorization]"
                                "(#section/Authentication-and-Authorization))",
                    "required": True,
                    "schema": {
                        "type": "string"
                    }
                },
                'query__where': {
                    "in": "query",
                    "name": "where",
                    "schema": {
                        "type": "object",
                    },
                    "description": "Apply a filter."
                                "<br />[(Cheatsheet)](#section/Cheatsheet)",
                },
                'query__max_results': {
                    "in": "query",
                    "name": "max_results",
                    "schema": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": app.config['PAGINATION_LIMIT'],
                        "default": app.config['PAGINATION_DEFAULT'],
                    },
                    "description": "Limit the number of results per page."
                                "<br />[(Cheatsheet)](#section/Cheatsheet)",
                },
                'query__page': {
                    "in": "query",
                    "name": "page",
                    "schema": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "description": "Specify result page."
                                "<br />[(Cheatsheet)](#section/Cheatsheet)",
                },
                'query__sort': {
                    "in": "query",
                    "name": "sort",
                    "schema": {
                        "type": "object",
                    },
                    "description": "Sort results."
                                "<br />[(Cheatsheet)](#section/Cheatsheet)",
                },
                'query__embedded': {
                    "in": "query",
                    "name": "embedded",
                    "schema": {
                        "type": "object",
                    },
                    "description": "Control embedding of related resources."
                                "<br />[(Cheatsheet)](#section/Cheatsheet)",
                },
                'query__projection': {
                    "in": "query",
                    "name": "projection",
                    "schema": {
                        "type": "object",
                    },
                    "description": "Show/hide fields in response."
                                "<br />[(Cheatsheet)](#section/Cheatsheet)",
                }
            }           
        }
    })

    add_documentation(swagger, {
        'components': {
            # Error Responses
            'responses': {
                '404': _create_error_message(404, 'No item with the provided `_id` exists'),
                '401': _create_error_message(401, 'The `Authorization` header is missing or '
                                                  'contains an invalid token'),
                '403': _create_error_message(403, 'The `Authorization` header contains a valid '
                                                  'token, but you do not have the required '
                                                  'permissions'),
                '422': _create_error_message(422, 'Validation of the document body failed', {
                        '_issues': {
                            "description": "The validation issues as a map between field and error message.",
                            "example": {
                                "<field1>": "required field",
                                "<field2>": "must be of objectid type"
                            },
                            "type": "object",
                            "title": "Map<String,String>",
                            "patternProperties": {
                                "^[a-zA-Z0-9]+$": { "type": "string" }
                            }
                        }
                    }),
                '428': _create_error_message(428, "The `If-Match` header is missing"),
                '412': _create_error_message(412, "The `If-Match` header does not match the "
                                                  "current `_etag`")
            }
        }
    })


def _add_param_refs(swagger, path, method, references):
    """Helper to add references to query parameters to a path method."""
    parameters = [{'$ref': '#/components/parameters/%s' % ref}
                  for ref in references]
    add_documentation(swagger, {
        'paths': {path: {method.lower(): {'parameters': parameters}}},
    })


def _add_error_refs(swagger, path, method, codes):
    """Helper to add references to error responses to a path method."""
    errors = {str(code): {'$ref': '#/components/responses/%s' % code}
              for code in codes}

    add_documentation(swagger, {
        'paths': {path: {method.lower(): {'responses': errors}}},
    })


def _update_properties(swagger, domain):
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
        add_documentation(swagger, {'definitions': {
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


def _update_paths(swagger, resource, domain):
    """Update the lookup paths for a resource.

    Re-format the default _id lookup and add additional lookups,
    if any exist.
    """
    title = domain['item_title']
    key = '%s__id' % title
    path = '/%s/{%sId}' % (resource, title.lower())

    updates = {'description': 'The `_id` field of a %s document' % title}
    add_documentation(swagger, {'parameters': {key: updates}})

    # try:
    #     lookup = domain['additional_lookup']
    # except KeyError:
    #     pass
    # else:
    #     field = lookup['field']
    #     params = [{
    #         'in': 'path',
    #         'name': field,
    #         'required': False,
    #         'description': '*Instead* of the `_id`, you can also use the '
    #                        '`%s` field as an alternative lookup when '
    #                        '*retrieving* a document.' % field,
    #         'type': lookup['url'],
    #     }]
    #     add_documentation(swagger, {
    #         'paths': {path: {'get': {'parameters': params}}},
    #     })


def _update_methods(swagger, resource, domain):
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

        if method == 'POST':
            errors.append(422)

        if has_data_relation:
            parameters.append('embedded')

        _add_error_refs(swagger, resource_path, method, errors)
        _add_param_refs(swagger, resource_path, method, parameters)

    # 2: Item methods, `GET`, `PATCH` and `DELETE` possible
    item_path = '/%s/{%sId}' % (resource, domain['item_title'].lower())

    try:
        # Prepare path for additional lookup if any.
        lookup = domain['additional_lookup']
        item_additional_path = '/%s/{%s}' % (resource, lookup['field'].capitalize())
    except KeyError:
        item_additional_path = None

    for method in domain['item_methods']:
        parameters = []
        errors = [404]  # all item methods can result in 404 if item is missing

        if method not in domain['public_item_methods']:
            errors += [401, 403]
            parameters.append('auth')

        if method == 'PATCH':
            errors += [412, 422, 428]

        if method in ['GET', 'PATCH']:
            if has_data_relation:
                parameters.append('embedded')

        if method == 'DELETE':
            errors += [412, 428]

        _add_error_refs(swagger, item_path, method, errors)
        _add_param_refs(swagger, item_path, method, parameters)

        # Apply the same modification also to the additional lookup path
        if method == 'GET' and item_additional_path is not None:
            _add_error_refs(swagger, item_additional_path, method, errors)
            _add_param_refs(swagger, item_additional_path, method, parameters)
