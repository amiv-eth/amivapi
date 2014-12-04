""" This is a list of which groups exist to grant permissions. It should be
possible to change anything without breaking stuff. """

roles = {
    'vorstand': {
        'users': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1
        },
        'permissions': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwards': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardusers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardaddresses': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'sessions': {
            'GET': 1,
            'DELETE': 1
        },
        'events': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'eventsignups': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'files': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'studydocuments': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'joboffers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'read-everything': {
        'users': {
            'GET': 1,
        },
        'permissions': {
            'GET': 1,
        },
        'forwards': {
            'GET': 1,
        },
        'forwardusers': {
            'GET': 1,
        },
        'forwardaddresses': {
            'GET': 1,
        },
        'sessions': {
            'GET': 1,
        },
        'events': {
            'GET': 1,
        },
        'eventsignups': {
            'GET': 1,
        },
        'files': {
            'GET': 1,
        },
        'studydocuments': {
            'GET': 1,
        },
        'joboffers': {
            'GET': 1,
        }
    },
    'event-admin': {
        'events': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'eventsignups': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'job-admin': {
        'files': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'joboffers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'mail-admin': {
        'forwards': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardusers': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'forwardaddresses': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    },
    'studydocs-admin': {
        'files': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        },
        'studydocuments': {
            'GET': 1,
            'POST': 1,
            'PATCH': 1,
            'PUT': 1,
            'DELETE': 1
        }
    }
}
