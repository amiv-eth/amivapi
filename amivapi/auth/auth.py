# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Custom AMIV Token auth class.

**FAQ**

    # Check if auth is enabled/disabled globally:
    from flask import current_app
    if current_app.auth:
        print("It's on!")

    # access authentication data of current user
    from flask import g
    g.get('current_user')       # user_id (str)
    g.get('current_token')      # token (str)
    g.get('current_session')    # session data (dict)

    # Check if the user is admin
    from flask import g
    if g.get('resource_admin'):
        print("Can see and change everything!")
    if g.get('resource_admin_readonly'):
        print('Can look at anything, but not necessarily change something.')

    # Why always g.get('something') instead g['something']?
    # If auth is disabled (e.g. for some tests) the values wont be in g!


**How to use**

1. Subclass `AmivTokenAuth`
2. implement only the methods `create_user_lookup_filter` and
   `has_write_permission` depending on your resource.
   Note: You shouldn't care about admin permissions. Those methods will only be
   called for non-admins!
3.  Use your auth class in your resource settings. Done!
4. Tip: You can still use all Eve settings like 'public_methods' and
   'public_item_methods'!

Take a look at `users.security` for an example.

**Don't want all this?**

Simply use a auth class that is *not* a subclass of AmivTokenAuth.

**How it works**

We are using Eve's hooks to add authentiation.
All methods go through the following methods:

- `AmivTokenAuth.authorized` (only if the methods is not public!)
- `authenticate`
- `abort_if_not_public`

For resource endpoints, nothing else happens.
Item endpoints have more logic:

- GET

  - `add_lookup_filter`
  - `AmivTokenAuth.create_user_lookup_filter`

- PATCH and DELETE

  - `check_write_permission`
  - `AmivTokenAuth.has_write_permission`
"""

from datetime import datetime as dt

from flask import current_app, g, request, abort
from eve.auth import BasicAuth, resource_auth


class AmivTokenAuth(BasicAuth):
    """Amiv authentication and authorization base class.

    Subclass and implement `has_write_permission` as well as
    `create_user_lookup_filter`.
    """

    def authorized(self, allowed_roles, resource, method):
        """Authorize Request.

        This is the method Eve will call if the endpoint is not public.

        We use this by setting `g.auth_required` to inform auth hook to abort
        later if user can't be identified.

        You shouldn't overwrite this when subclassing `AmivTokenAuth`.
        """
        g.auth_required = True
        return True

    def has_write_permission(self, user_id, item):
        """Check if *user* is allowed to PATCH or DELETE *item*.

        Implement this function for your resource.

        Args:
            user (str): The id of the user that wants to access the item
            item (dict): The item the user wants to change or delete.

        Returns:
            bool: True if user has permission to change the item, False if not.
        """
        return False

    def create_user_lookup_filter(self, user_id):
        """Create a filter for item lookup in GET, PATCH and DELETE.

        Implement this function for your resource.

        Args:
            user_id (str): The id of the user

        Returns:
            dict: The filter, will be combined with other filters in the hook.
                Return None or empty dict if no filters should be applied.
        """
        return None


# Hooks begin here

def authenticate(*args, **kwargs):
    """Authenticate user.

    This is not part of the auth class because we want authentication for
    public resources as well.

    Recognized tokens in following formats:
    - Basic auth with token as user and no password
    - "Authorization: <token>"
    - "Authorization: Token <token>"
    - "Authorization: Bearer <token>"

    Then look for sessions and user and check if root.

    Set the variables:

    - `g.current_token` (str): Token of current request, None if not provided.
    - `g.current_session` (dict): The current session, None if not found.
    - `g.current_user` (str): The id of the currently logged in user, None if
      not found.

    - `g.resouce_admin` (bool): True if user can see and change anything
    - `g.resource_admin_readonly` (bool): True if user can see anything

    Note: `current_token` & `current_session` are set to provide the info to
    other parts of the API if necessary (e.g. to check for API keys)
    """
    # Set defaults
    g.current_token = g.current_session = g.current_user = None
    g.resource_admin = g.resource_admin_readonly = False

    # Get token
    token = getattr(request.authorization, 'username', None)

    # Code copied from Eve's TokenAuth - parse different header formats
    if not token and request.headers.get('Authorization'):
        token = request.headers.get('Authorization').strip()
        if token.lower().startswith(('token', 'bearer')):
            token = token.split(' ')[1]
    # End of code copied from Eve

    if token:
        g.current_token = token

        # Get session
        sessions = current_app.data.driver.db['sessions']
        session = sessions.find_one({'token': token})

        if session:
            # Update timestamp (remove microseconds to match mongo precision)
            new_time = dt.utcnow().replace(microsecond=0)
            sessions.update_one({'_id': session['_id']},
                                {'$set': {
                                    '_updated': new_time
                                }})
            session['_updated'] = new_time

            # Save user_id and session with updated timestamp in g
            g.current_session = session
            g.current_user = session['user_id']

            # Check if root
            if g.current_user == str(current_app.config['ROOT_ID']):
                g.resource_admin = True

    # Idea to give other modules the possibility to check auth
    # e.g. groups or api keys
    # Call a signal the other modules can subscribe to
    # Can use either blinker (from flask) or Events (from eve)
    # No need to pass arguments or collect return values (just use g object)
    # e.g. Events:
    # current_app.after_authentication()


def abort_if_not_public(*args, **kwargs):
    """Abort if the resource is not public and there is no user/admin.

    Active if `g.auth_required` is set, i. e. the method is not public.

    Note: we also check for admin because e.g. API-keys can have admin rights
    without a specific user.
    """
    if g.get('auth_required') and not (g.current_user or
                                       g.resource_admin or
                                       g.resource_admin_readonly):
        current_app.logger.debug("Access denied.")  # TODO(Alex): Improve this
        abort(401)


def add_lookup_filter(resource, request, lookup):
    """Get and add lookup filter for GET, PATCH and DELETE.

    For both `resource_admin` and `resource_admin_readonly` there will be no
    filter.
    """
    if not(g.resource_admin or g.resource_admin_readonly):
        auth = resource_auth(resource)

        if isinstance(auth, AmivTokenAuth):
            extra_lookup = auth.create_user_lookup_filter(g.current_user)

            if extra_lookup:
                # Add the additional lookup with an `and` condition
                # or extend existing `$and`s
                lookup.setdefault('$and', []).append(extra_lookup)


def check_write_permission(resource, item):
    """Check if the user is allowed to PATCH or DELETE the item.

    `resouce_admin`s can write everything.
    """
    if not g.resource_admin:
        auth = resource_auth(resource)

        if isinstance(auth, AmivTokenAuth) and \
                not auth.has_write_permission(g.current_user, item):
            current_app.logger.debug("Access denied.")  # TODO(Alex): Improve
            abort(403)
