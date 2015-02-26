import hashlib
from os import urandom
from base64 import b64encode, b64decode

from flask import current_app as app
from flask import Blueprint, abort, request, g

from eve.render import send_response
from eve.methods.post import post_internal
from eve.methods.common import resource_link, payload
from eve.auth import TokenAuth
from eve.utils import home_link, config, debug_error_message

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.inspection import inspect

import models
import permission_matrix
import utils

"""
This file provides token based authentification. A user can POST the /sessions
resource to obtain a token.
"""


""" Creates a new hash for a password. This generates a random salt, so it can
not be used to check hashes!
"""


def create_new_hash(password):
    salt = urandom(16)
    password = bytearray(password, 'utf-8')
    return (
        b64encode(salt) +
        '$' +
        b64encode(hashlib.pbkdf2_hmac('SHA256', password, salt, 100000))
    )


""" This function (HACK ALERT) tries to figure out where relationship would
point to if an object was created with the passed request. If somebody finds
a better way to check permissions please consider changing this. We depend
on a lot of knowledge of relationship internals. """


def resolve_future_field(model, payload, field):
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


""" Beginning of actual authentification process """


class TokenAuth(TokenAuth):
    """ We could have used eve's allowed_roles parameter, but that does not
    support roles on endpoint level, but only on resource level """
    def check_auth(self, token, allowed_roles, resource, method):
        dbsession = app.data.driver.session

        try:
            sess = dbsession.query(models.Session).filter(
                models.Session.token == token).one()
        except NoResultFound:
            error = ("Access denied for %s %s: unknown token %s"
                     % (method, resource, token))
            app.logger.debug(error)
            abort(401, description=debug_error_message(error))

        g.logged_in_user = sess.user_id
        g.apply_owner_filters = False
        g.resource_admin_access = False

        if sess.user_id == 0:
            app.logger.debug("Access granted for root user %s %s"
                             % (method, resource))
            g.resource_admin_access = True
            return True

        permissions = dbsession.query(models.Permission) \
            .filter(models.Permission.user_id == sess.user_id).all()
        for permission in permissions:
            try:
                if permission_matrix. \
                        roles[permission.role][resource][method] == 1:
                    g.resource_admin_access = True
                    app.logger.debug("Access granted to %s %s "
                                     % (method, resource)
                                     + "for user %i with role %s"
                                     % (g.logged_in_user, permission.role))
                    return True
            except KeyError:
                pass

        resource_class = utils.get_class_for_resource(resource)

        if request.method in resource_class.__registered_methods__:
            app.logger.debug("Access granted to %s %s for registered user %i"
                             % (method, resource, g.logged_in_user))
            return True

        if request.method in resource_class.__owner_methods__:
            app.logger.debug("Access granted to %s %s for owner user %i"
                             % (method, resource, g.logged_in_user))
            g.apply_owner_filters = True
            return True

        error = ("Access denied to %s %s for unpriviledged user %i"
                 % (method, resource, g.logged_in_user))
        app.logger.debug(error)
        abort(403, description=debug_error_message(error))


""" Authentification related endpoints """

auth = Blueprint('auth', __name__)


""" Endpoints """


""" Login

A POST to /sessions exspects a username and password. If they are correct a
token is created and used to register a session in the database, which is sent
back to the user.

If the user is not found we try to import the user via LDAP, if he is found we
update his data
"""


@auth.route('/sessions', methods=['POST'])
def process_login():
    p_data = payload()
    if 'username' not in p_data:
        abort(422, description=debug_error_message(
            "Please provide a username."))
    if 'password' not in p_data:
        abort(422, description=debug_error_message(
            "Please provide the password."))

    user = app.data.driver.session.query(models.User).filter_by(
        username=p_data()['username']).all()

    if(len(user) == 1):
        (salt, hashed_password) = user[0].password.split('$')
        salt = b64decode(salt)
        hashed_password = b64decode(hashed_password)
        sent_password = bytearray(p_data()['password'],
                                  'utf-8')

        if hashed_password != hashlib.pbkdf2_hmac(
                'SHA256',
                sent_password,
                salt,
                100000
        ):
            error = "Wrong login: Password does not match!"
            app.logger.debug(error)
            abort(401, description=debug_error_message(error))

        token = b64encode(urandom(256))
        response = post_internal(
            'sessions',
            {
                'user_id': user[0].id,
                'token': token
            }
        )
        return send_response('sessions', response)

    error = "Wrong login: User not found!"
    app.logger.debug(error)
    abort(401, description=debug_error_message(error))


""" GET to /roles """


@auth.route('/roles', methods=['GET'])
def get_roles():
    if app.auth and not app.auth.authorized([], 'roles', 'GET'):
        return app.auth.authenticate()

    response = {}

    items = []
    for role, perms in permission_matrix.roles.items():
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


""" Auth related hooks """


""" Permission filters for all requests """


def pre_get_permission_filter(resource, request, lookup):
    """ This function adds filters to the lookup parameter to only return
    items, which are owned by the user for resources, which are neither
    public nor open to registered users
    """
    resource_class = utils.get_class_for_resource(resource)
    if request.method in resource_class.__public_methods__ \
            or not g.apply_owner_filters:
        return

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


def check_future_object_ownage_filter(resource, request, obj):
    """ Check if an object would have the currently logged in user as an owner
    if the passed obj was created in the database or an existing object
    patched to contain the data
    """
    resource_class = utils.get_class_for_resource(resource)
    if request.method in resource_class.__public_methods__ \
            or not g.apply_owner_filters:
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


# TODO(Conrad): Does this work with bulk insert?
def pre_post_permission_filter(resource, request):
    check_future_object_ownage_filter(resource, request, payload())


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
    check_future_object_ownage_filter(resource, request, data)


def pre_delete_permission_filter(resource, request, lookup):
    pre_get_permission_filter(resource, request, lookup)


""" Hooks to add _author field to all database inserts """


def set_author_on_insert(resource, items):
    _author = getattr(g, 'logged_in_user', -1)
    for i in items:
        i['_author'] = _author


def set_author_on_replace(resource, item, original):
    set_author_on_insert(resource, [item])


""" Hooks to hash passwords when user entries are changed in the database """


def hash_password_before_insert(users):
    for u in users:
        if 'password' in u:
            u['password'] = create_new_hash(u['password'])


def hash_password_before_update(user, original_user):
    hash_password_before_insert([user])


def hash_password_before_replace(user, original_user):
    hash_password_before_insert([user])
