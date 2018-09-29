"""Remote procedure calls."""

from amivapi.utils import register_domain  # , register_validator


class RPCAuth():
    """Authenticate RPC requests."""


rpcdomain = {
    'rpc': {
        'schema': {
            'function': {
                'type': 'rpc_function',
            },
            'arguments': {
                'type': 'rpc_arguments',
                'dependencies': ['function'],
            },
            'result': {
                'type': 'string',
                'readonly': True,
            }
        },

        'authentication': RPCAuth,

        'resource_methods': ['GET', 'POST'],
        'item_methods': ['GET', 'DELETE'],
    }
}


def init_app(app):
    """Add the rpc endpoint and validation to the app."""
    register_domain(app, rpcdomain)
