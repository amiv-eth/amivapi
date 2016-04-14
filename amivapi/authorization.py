# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

""" This file contains functions and hooks to authorize requests based on the
authentificated user.

The global variable g.resource_admin will be set to True if the user has an
admin role for the endpoint, otherwise to False
"""


from flask import current_app as app
from flask import abort, request, g

from eve.utils import config, debug_error_message

from amivapi import utils


def common_authorization(resource, method):
    """ Determine the type of authorization check we have to make and execute
    checks common to all methods. Also this will perform authentication if
    it has not been done already(public methods skip it).

    Returns whether the user has been authorized. If he has not been
    authorized this may still happen later due to ownership of an object.
    See authorize_object_change() or pre_get_permission_change() for owner
    based authorization.

    This will abort if there is no owner attribute for the requested resource
    and no other means of authorization were met.

    The permissions will be determined based on the authorization attributes of
    the class for the requested resource in models.py, so if you want to use
    this for a custom endpoint make sure to create a class there with the
    desired authorization attributes.

    This will:
        1. Allow or abort apikey access based on config
            => return True if endpoint in config, g.resource_admin = True
            => else abort(403)
        2. Check if the user is root
            => return True, g.resource_admin = True
        3. Check if the user is in a group that gives admin permissions
                for the endpoint and method
            => return True, g.resource_admin = True
        4. Check if the endpoint is public
            => return True, g.resource_admin = False
        5. Abort(401) anonymous users without token
        6. Check if the endpoint is open to registered users
            => return True, g.resource_admin = False
        7. Check if the endpoint is open to owners
            => return False, g.resource_admin = False
        8. abort(403)

    API keys:
        This function also checks authorization for apikeys if one has been
        sent instead of a token. If the endpoint is allowed for that endpoint
        True will be returned, else aborted immediately

    :param resource: The requested resource
    :param method: The requested method

    :returns: Has the user been authorized? If this returns false it is still
              possible that the user should be authorized, as owner based
              access is not checked. For examples how to do that see the hooks
              below
    """
    resource_domain = app.config['DOMAIN'][resource]

    # Allow if authentication is disabled
    if not app.auth:
        g.logged_in_user = 0
        g.resource_admin = 1
        return True

    # If the method is public or this is called by a custom endpoint,
    # authentication has not been performed yet automatically. If the user
    # has set a token, check that now to generate g.logged_in_user. If he has
    # no token, set user ID to -1
    if (not hasattr(g, 'logged_in_user') and
            not app.auth.authorized([], resource, method)):
        g.logged_in_user = -1

    g.resource_admin = True

    # Access via API key
    if hasattr(g, 'apikey'):
        try:
            if config.APIKEYS[g.apikey][resource][method] == 1:
                app.logger.debug("Access via API key %s granted for %s to %s"
                                 % (config.APIKEYS[g.apikey]['name'],
                                    resource, method))
                return True
        except KeyError:
            pass
        abort(403)

    # User is root -> allow
    if g.logged_in_user == 0:
        app.logger.debug("Access granted for root user %s %s"
                         % (method, resource))
        return True

    # User is in a group with admin rights for this method-> allow
    if utils.check_group_permission(g.logged_in_user, resource, method):
            app.logger.debug("Access granted to %s %s "
                             "for user %i"
                             % (method, resource, g.logged_in_user))
            return True

    g.resource_admin = False

    # Method is public -> allow
    if method in resource_domain['public_methods']:
        return True

    if g.logged_in_user == -1:
        app.logger.debug("Aborted(401) user without token on non public "
                         "method")
        abort(401)

    # Endpoint is open to registered users -> allow
    # Anonymous users won't arrive here as they have already been
    if method in resource_domain['registered_methods']:
        app.logger.debug("Access granted to %s %s for registered user %i"
                         % (method, resource, g.logged_in_user))
        return True

    # Endpoint is open to object owners -> allow, but inform caller to
    # perform more checks
    if request.method in resource_domain['owner_methods']:
        return False

    # No permission, abort
    error = ("Access denied to %s %s for unpriviledged user %i"
             % (method, resource, g.logged_in_user))
    app.logger.debug(error)
    abort(403, description=debug_error_message(error))


def _create_lookup_owner_filter(resource):
    """ This function creates the filter

    :param lookup: The lookup to manipulate
    :param resource: Resource name(used to get owner)
    :returns: Dict with or conditions
    """
    resource_domain = app.config['DOMAIN'][resource]

    if 'owner' not in resource_domain:
        abort(403)

    # [:] copies the list (and looks like a weird chest with a buttoned shirt
    fields = resource_domain['owner'][:]

    conditions = []

    # We loop through all owner fields and for each field we generate a filter
    # which will allow the owner to see the object.
    for field in fields:
        if '.' not in field:
            # owner id is simple field of the class
            conditions.append({field: g.logged_in_user})
        else:
            # owner id is over relation
            conditions.append(
                {"__self__": "indirect_any(\"%s,%i\")"
                    % (field, g.logged_in_user)})

    return {'or_': conditions}


def apply_lookup_owner_filters(lookup, resource):
    """ This function adds filters to the lookup, so the results will only
    contain objects which belong to the user(using the owner feature).

    :param lookup: The lookup to manipulate
    :param resource: Resource name(used to find the model)
    """
    owner_filter = _create_lookup_owner_filter(resource)

    # Make sure the auth is in an and_ statement,
    # otherwise authorization could be avoided be adding
    # ?where={"_or":[{<something true}]} to the request
    if 'and_' not in lookup:
        lookup['and_'] = []
    lookup['and_'].append(owner_filter)


#
#
# Permission hooks for all requests
#
#


def pre_get_permission_filter(resource, request, lookup):
    """ This hook adds filters to the lookup parameter to only return
    items, which are owned by the user for resources, which are neither
    public nor open to registered users

    :param resource: requested resource
    :param request: The request object
    :param lookup: The lookup dict to filter results
    """
    if not common_authorization(resource, request.method):
        apply_lookup_owner_filters(lookup, resource)


# TODO(Conrad): Does this work with bulk insert?
def pre_post_permission_filter(resource, request):
    """ Hook to apply authorization to POST requests
    Since POST cant be a owner method common auth will never return False
    Just call it to make sure the request globals are set


    :param resource: requested resource
    :param request: The request object
    """
    common_authorization(resource, request.method)


def pre_put_permission_filter(resource, request, lookup):
    """ Hook to apply authorization to PUT requests

    :param resource: requested resource
    :param request: The request object
    :param lookup: The lookup dict to filter results
    """
    if not common_authorization(resource, request.method):
        apply_lookup_owner_filters(lookup, resource)


def pre_patch_permission_filter(resource, request, lookup):
    """ This filter let's owners only patch objects they own

    The hook for patch is split into two parts. The first part is needed to
    apply filters to lookup before the object to be patched is extracted, the
    second one will examine the changes to be made to that object. Because of
    that split we have to store the result of the common_authorization function
    which tells us whether the user was already authorized in a different way
    than ownership, so we do not have to check ownership again(other means
    include admin priviledges, the method being public or open to registered
    user, see common_authorization() above)

    :param resource: requested resource
    :param request: The request object
    :param lookup: The lookup dict to filter results
    """

    # We use this to pass the result to the hook below
    g.authorized_without_ownership = common_authorization(resource,
                                                          request.method)
    if not g.authorized_without_ownership:
        apply_lookup_owner_filters(lookup, resource)


def pre_delete_permission_filter(resource, request, lookup):
    """ Hook to apply authorization to DELETE requests, works the same as the
    filter for GET

    :param resource: requested resource
    :param request: The request object
    :param lookup: The lookup dict to filter results
    """
    pre_get_permission_filter(resource, request, lookup)


def group_visibility_filter(request, lookup):
    """ Hook to filter GET requests to /groups
    Other methods are not concerned because normal owner filters
    suffice.
    But since some groups are open for self enrollment users must be
    able to find those groups

    Therefore groups are visible either for their owners or for
    everybody if self enrollment is allowed

    This essentially works like "apply_lookup_owner_filter",
    but extends the or statement

    This rules do not apply to admins

    :param lookup: The lookup to manipulate
    :param resource: Resource name(used to find the model)
    """
    if not g.resource_admin:
        group_filter = _create_lookup_owner_filter("groups")

        # visible if user is owner OR self enrollment is permitted
        group_filter['or_'].append({'allow_self_enrollment': True})

        # see apply_lookup_owner_filter why this is important
        if 'and_' not in lookup:
            lookup['and_'] = []
        lookup['and_'].append(group_filter)

#
#
#  Hooks to customize users resource to restrict on field level
#
#


def pre_users_get(request, lookup):
    """ Prevent extraction of password hashes

    :param request: The request object
    :param lookup: The lookup dict(unused)
    """
    projection = request.args.get('projection')
    if projection and 'password' in projection:
        abort(403, description='Bad projection field: password')
