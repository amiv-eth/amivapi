from flask import current_app as app
from flask import Blueprint, abort, request, g

from eve.methods.common import resource_link, payload
from eve.utils import home_link, config, debug_error_message
from eve.render import send_response

from sqlalchemy.inspection import inspect

import models
import utils

""" This file contains functions and hooks to authorize requests based on the
authentificated user.

The global variable g.resource_admin will be set to True if the user has an
admin role for the endpoint, otherwise to False
"""


def common_authorization(resource, method):
    """ Determine the type of authorization check we have to make and execute
    checks common to all methods. Also this will perform authentification if
    it has not been done already(public methods skip it).

    Returns whether additional owner checks have to be performed

    This will:
        1. Check if the user is root
            => return False, g.resource_admin = True
        2. Check if the user has a role, which allowes everything for this
            endpoint
            => return False, g.resource_admin = True
        3. Check if the endpoint is public
            => return False, g.resource_admin = False
        4. Check if the endpoint is open to registered users
            => return False, g.resource_admin = False
        5. Check if the endpoint is open to owners
            => return True, g.resource_admin = False
        6. abort(403)
    """
    resource_class = utils.get_class_for_resource(resource)

    # If the method is public, authentification has not been performed by eve
    # automatically. If the user has set a token check that now to generate
    # g.logged_in_user. If he has no token, set user ID to -1
    if method in resource_class.__public_methods__:
        if not app.auth or not app.auth.authorized([], resource, method):
            g.logged_in_user = -1

    g.resource_admin = True

    # User is root -> allow
    if g.logged_in_user == 0:
        app.logger.debug("Access granted for root user %s %s"
                         % (method, resource))
        return False

    # User has admin role for this endpoint -> allow
    permissions = app.data.driver.session.query(models.Permission) \
        .filter(models.Permission.user_id == g.logged_in_user).all()
    for permission in permissions:
        try:
            if config. \
                    ROLES[permission.role][resource][method] == 1:
                app.logger.debug("Access granted to %s %s "
                                 % (method, resource)
                                 + "for user %i with role %s"
                                 % (g.logged_in_user, permission.role))
                return False
        except KeyError:
            pass

    g.resource_admin = False

    # Method is public -> allow
    if method in resource_class.__public_methods__:
        return False

    # Endpoint is open to registered users -> allow
    # Anonymous users won't arrive here as they are already aborted during
    # authentification if it is required
    if method in resource_class.__registered_methods__:
        app.logger.debug("Access granted to %s %s for registered user %i"
                         % (method, resource, g.logged_in_user))
        return False

    # Endpoint is open to object owners -> allow, but inform caller to
    # perform more checks
    if request.method in resource_class.__owner_methods__:
        app.logger.debug("Access granted to %s %s for owner user %i"
                         % (method, resource, g.logged_in_user))
        return True

    # No permission, abort
    error = ("Access denied to %s %s for unpriviledged user %i"
             % (method, resource, g.logged_in_user))
    app.logger.debug(error)
    abort(403, description=debug_error_message(error))


def resolve_future_field(model, payload, field):
    """ This function (HACK ALERT) tries to figure out where a relationship
    would point to if an object was created with the passed request. If
    somebody finds a better way to check permissions please consider changing
    this. We depend on a lot of knowledge of relationship internals. """
    field_parts = field.split('.')  # This looks like an emoticon

    if len(field_parts) == 1:
        return payload[field]

    relationship = inspect(model).relationships[field_parts[0]]

    query = app.data.driver.session.query(relationship.target)
    for l, r in relationship.local_remote_pairs:
        query = query.filter(r.__eq__(payload[l.name]))

    value = query.one()

    for part in field_parts[1:]:
        value = getattr(value, part)

    return value


def authorize_object_change(resource, request, obj):
    """ Check if an object would have the currently logged in user as an owner
    if the passed obj was created in the database or an existing object
    patched to contain the data
    """
    resource_class = utils.get_class_for_resource(resource)

    # Perform common authorization tasks and return if we do not need to do
    # more
    if not common_authorization(resource, request.method):
        return

    if not hasattr(resource_class, '__owner__'):
        app.logger.error("Warning: Resource %s has no __owner__" % resource +
                         "but defines __owner_methods__!")
        abort(500, description="There seems to be a major"
              + " bug in the AMIV API. Please report how you arrived here to "
              + "it@amiv.ethz.ch.")

    try:
        for field in resource_class.__owner__:

            v = resolve_future_field(resource_class, obj, field)
            if v == g.logged_in_user:
                app.logger.debug("Permission granted base on new owner"
                                 + "field %s " % field + "with value %s" % v)
                return True
    except AttributeError:
        app.logger.error("Unknown owner field for %s: %s" % (resource, field))
        raise

    error = ("403 Access forbidden: The sent object would not belong "
             + "to the logged in user after this POST.")
    app.logger.debug(error)
    abort(403, description=debug_error_message(error))


""" Permission filters for all requests """


def pre_get_permission_filter(resource, request, lookup):
    """ This function adds filters to the lookup parameter to only return
    items, which are owned by the user for resources, which are neither
    public nor open to registered users
    """
    if not common_authorization(resource, request.method):
        return

    resource_class = utils.get_class_for_resource(resource)

    if not hasattr(resource_class, '__owner__'):
        app.logger.error("Warning: Resource %s has no __owner__" % resource +
                         "but defines __owner_methods__!")
        abort(500, description="There seems to be a major"
              + " bug in the AMIV API. Please report how you arrived here to "
              + "it@amiv.ethz.ch.")

    fields = resource_class.__owner__[:]

    # Every condition is, that the field is equal to the user id
    conditions = map(lambda x: x + "==" + str(g.logged_in_user), fields)
    # Concatenate all conditions with or
    condition_string = reduce(lambda x, y: x + " or " + y, conditions)

    lookup[condition_string] = ""


# TODO(Conrad): Does this work with bulk insert?
def pre_post_permission_filter(resource, request):
    authorize_object_change(resource, request, payload())


def pre_put_permission_filter(resource, request, lookup):
    pre_delete_permission_filter(resource, request, lookup)
    pre_post_permission_filter(resource, request)
    return


def pre_patch_permission_filter(resource, request, lookup):
    """ This filter let's owners only patch objects they own """
    pre_get_permission_filter(resource, request, lookup)


def update_permission_filter(resource, updates, original):
    """ This filter ensures, that an owner can not change the owner
    of his objects """

    data = original.copy()
    data.update(updates)
    authorize_object_change(resource, request, data)


def pre_delete_permission_filter(resource, request, lookup):
    pre_get_permission_filter(resource, request, lookup)


""" GET to /roles """

permission_info = Blueprint('permission_info', __name__)


@permission_info.route('/roles', methods=['GET'])
def get_roles():
    if app.auth and not app.auth.authorized([], 'roles', 'GET'):
        return app.auth.authenticate()

    response = {}

    items = []
    for role, perms in config.ROLES.items():
        for p in perms.values():
            for k in ['GET', 'POST', 'PATCH', 'PUT', 'DELETE']:
                if k not in p.keys():
                    p[k] = 0
        items.append({
            'name': role,
            'permissions': perms
        })
    response[config.ITEMS] = items

    response[config.LINKS] = {
        'parent': home_link(),
        'self': {
            'title': 'roles',
            'href': resource_link()
        }
    }

    return send_response(None, [response])


""" Hooks to customize users resource """


def pre_users_get(request, lookup):
    """ Prevent extraction of password hashes """
    projection = request.args.get('projection')
    if projection and 'password' in projection:
        abort(403, description='Bad projection field: password')


def pre_users_patch(request, lookup):
    """ Hook for the /users resource to prevent people from changing fields
    which are imported via LDAP """
    if g.resource_admin:
        return

    disallowed_fields = ['username', 'firstname', 'lastname', 'birthday',
                         'legi', 'nethz', 'department', 'phone',
                         'ldapAddress', 'gender', 'membership']

    data = payload()

    for f in disallowed_fields:
        if f in data:
            app.logger.debug("Rejecting patch due to insufficent priviledges"
                             + "to change " + f)
            abort(403, description=(
                'You are not allowed to change your ' + f
            ))
