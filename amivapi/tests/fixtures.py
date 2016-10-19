
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Utilities for fixture loading and easy object creation in tests

There are two basic ways to use the system in tests. Either a dictionary
describing many object can be used with load_fixture or a single object
can be created with new_object.

Example of big state:

self.load_fixture({
    'users': [
        {
            'nethz': 'pablo',
            'rfid': '132432'
        }
    ],
    'events': [
        {
            'title': 'mytestevent'
        }
    ]
})

Just creating one object:

user1 = new_object('users', nethz='Pablo', rfid='123456')

Note that the second method might be more useful, if you need the created
objects fields like IDs.


Supporting custom validators:

Before fields are filled with random values, custom preprocessing functions are
called for each resources. Use those to fill in any fields, which have custom
validators and will therefore reject random values.

See preprocess_sessions or preprocess_events below for examples
"""

import random
import string
import pytz
from bson import ObjectId
from datetime import datetime, date, timedelta

from flask import current_app
from eve.methods.post import post_internal

from amivapi.settings import ROOT_PASSWORD, ROOT_ID, EMAIL_REGEX
from amivapi.utils import admin_permissions


class BadFixtureException(Exception):
    """Exception that can be raised for bad tests."""
    pass


class FixtureMixin(object):
    """class to be inherited from to allow fixture loading"""
    def new_object(self, resource, **kwargs):
        """Create one object of the given resource. Fill in necessary values.

        Example:
            user1 = new_object('users', nethz='Pablo', rfid='123456')
        """
        return self.load_fixture({resource: [kwargs]})[0]

    def load_fixture(self, fixture):
        """Load a dictionary as initial database state.

        Missing fields are filled in using defaults, or if not available with
        random values. Note that this describes post requests, so for example
        a session will need username and password, not user and token.

        Returns:
            A list of all created objects

        Example:
        self.load_fixture({
            'users': [
                {
                    'nethz': 'pablo',
                    'rfid': '132432'
                }
            ],
            'events': [
                {
                    'title': 'mytestevent'
                }
            ]
        })
        """
        added_objects = []

        # We need to sort in the order of dependencies. It is for example
        # not possible to add sessions before we have users, as we need valid
        # object IDs for the relations.
        for resource, obj in self.sorted_by_dependencies(fixture):
            schema = self.app.config['DOMAIN'][resource]['schema']

            # Note that we pass the current state of the fixture to resolve
            # fields, which depend on already inserted content
            self.preprocess_fixture_object(resource, schema, obj, fixture)

            # Add it to the database
            with self.app.test_request_context("/" + resource, method='POST'):
                with admin_permissions():
                    response, _, _, return_code = post_internal(resource, obj)
                if return_code != 201:
                    raise BadFixtureException("Fixture could not be loaded:\n"
                                              "%s\nProblem was caused by:\n%s"
                                              % (repr(response), obj))
            added_objects.append(response)

        # Check that everything went fine
        if len(added_objects) < sum([len(v) for v in fixture.values()]):
            raise BadFixtureException("Not all objects in the fixture could be "
                                      "added! Check your dictionary!")

        return added_objects

    def preprocess_fixture_object(self, resource, schema, obj, fixture):
        """Fills in missing fields in a fixture's objects."""

        # Call resource dependent function.
        preprocess_func = getattr(self, 'preprocess_%s' % resource, None)
        if preprocess_func:
            preprocess_func(schema, obj, fixture)
        
        # We iterate over the schema to fix missing fields with random values
        for field, field_def in schema.items():
            if (field not in obj
                    and field_def.get('required', False)
                    and not field_def.get('readonly', False)):
                # We need to add a value for the field to create a valid
                # object
                if 'default' in field_def:
                    obj[field] = field_def['default']
                else:
                    # Create a random value
                    obj[field] = self.create_random_value(field_def)

    def preprocess_users(self, schema, obj, fixture):
        if 'password' not in obj:
            # Fill in a password, this is necessary in case we want to login
            # using a post to sessions. preprocess_sessions depends on this
            obj['password'] = ''.join(
                random.choice(string.ascii_letters + string.digits)
                for _ in range(30))

    def preprocess_sessions(self, schema, obj, fixture):
        """We need to fill correct usernames and passwords for sessions, so
        they are special"""

        # If no username, make a random session
        obj.setdefault('username', str(random.choice(
            list(self.db['users'].find({})))['email']))

        if 'password' not in obj:
            username = obj['username']
            if username in (u'root', str(ROOT_ID),
                            self.app.config['ROOT_MAIL']):
                obj['password'] = ROOT_PASSWORD
            else:
                # find the user in the fixture and insert his password
                for user in fixture['users']:
                    if username in (user.get('nethz'),
                                    user.get('email'),
                                    str(user.get('_id'))):
                        obj['password'] = user['password']

            if 'password' not in obj:
                raise BadFixtureException(
                    "Could not determine password for user %s in fixture with "
                    "unspecified password for session %s"
                    % (obj['username'], obj))

    def preprocess_events(self, schema, obj, fixture):
        """Event validators are pretty complex, so do all thing with custom
        validators by hand"""
        # Add either german or englisch texts
        if random.choice([True, False]):
            obj.setdefault(
                'title_de',
                self.create_random_value(schema['title_de']))
            obj.setdefault(
                'catchphrase_de',
                self.create_random_value(schema['catchphrase_de']))
            obj.setdefault(
                'description_de',
                self.create_random_value(schema['description_de']))
        else:
            obj.setdefault(
                'title_en',
                self.create_random_value(schema['title_en']))
            obj.setdefault(
                'catchphrase_en',
                self.create_random_value(schema['catchphrase_en']))
            obj.setdefault(
                'description_en',
                self.create_random_value(schema['description_en']))

        # add some number of spots. If not specified different, we default
        # to have a signup, so possibly created signups will have something
        # to have relations to
        obj.setdefault('spots', random.randint(50, 500))
        if obj['spots']:
            if ('time_register_start' not in obj
                    and 'time_register_end' not in obj):
                obj['time_register_start'] = (
                    datetime.now(pytz.utc) - timedelta(
                        seconds=random.randint(0, 1000000)))
                obj['time_register_end'] = (
                    datetime.now(pytz.utc) + timedelta(
                        seconds=random.randint(0, 1000000)))
            else:
                if ('time_register_start' not in obj
                        or 'time_register_end' not in obj):
                    raise BadFixtureException(
                        "Bad fixture: please specify either both "
                        "time_register_start and time_register_end or none")

            obj.setdefault('allow_email_signup',
                           random.choice([True, False]))

    def preprocess_eventsignups(self, schema, obj, fixture):
        """Find random unique combination of user/event"""
        if 'user' not in obj and 'email' not in obj:
            users = [u['_id'] for u in self.db['users'].find()]
        else:
            users = [obj['user']]

        if 'event' not in obj:
            events = [ev['_id'] for ev in
                      self.db['events'].find({'spots': {'$ne': None}})]
        else:
            events = [obj['event']]
            
        random.shuffle(events)
        random.shuffle(users)
            
        for ev in events:
            for u in users:
                if self.db['eventsignups'].find(
                        {'event': ev, 'user': u}).count() == 0:
                    obj['event'] = ev
                    obj['user'] = u
                    return

        raise BadFixtureException("Requested eventsignup creation, but no "
                                  "unique user/event combination is "
                                  "available anymore. Parsed object: %s"
                                  % obj)            
            
    def create_random_value(self, definition):
        """Create a random value for the given cerberus field description."""
        # If there is a list of allowed values, just pick one
        if 'allowed' in definition:
            return random.choice(definition['allowed'])

        t = definition['type']
        if t == 'string':
            minimum_length = 0 if definition.get('empty', True) else 1
            length = random.randint(minimum_length,
                                    definition.get('maxlength', 100))

            if 'regex' in definition:
                if definition['regex'] == EMAIL_REGEX:
                    return "%s@%s.%s" % (
                        ''.join(random.choice(string.ascii_letters +
                                              string.digits)
                                for _ in range(max(1, length - 27))),
                        ''.join(random.choice(string.ascii_letters +
                                              string.digits)
                                for _ in range(20)),
                        ''.join(random.choice(string.ascii_letters +
                                              string.digits)
                                for _ in range(5)))
                raise NotImplementedError

            return ''.join(random.choice(string.ascii_letters + string.digits)
                           for _ in range(length))

        elif t == 'boolean':
            return random.choice([True, False])

        elif t == 'date':
            return datetime.date.fromordinal(
                random.randint(0, date.max.toordinal()))

        elif t == 'datetime':
            return datetime.fromtimestamp(
                random.randint(0, 2**32)).replace(tzinfo=pytz.utc)

        elif t == 'float':
            return random.rand() * random.randint(0, 2**32)

        elif t in ('number', 'integer'):
            return random.randint(0, 2**32)

        elif t == 'objectid':
            if 'data_relation' in definition:
                related_res = definition['data_relation']['resource']
                return random.choice(list(self.db[related_res].find()))['_id']
            return ObjectId(''.join(random.choice(string.hexdigits)
                                    for _ in range(24)))

        raise NotImplementedError

    def sorted_by_dependencies(self, fixture):
        """Sort fixtures by dependencies.

        Generator to yield a fixture in an order, which can be added to the
        database. It is not possible to add objects, which reference other
        objects, before those have been added to the database. Therefore we
        build a dependency map and yield only objects, which have their
        dependencies resolved.

        Yields:
            (resource, object) pairs
        """
        deps = {}
        for resource, resource_def in self.app.config['DOMAIN'].items():
            deps[resource] = set(
                field_def.get('data_relation', {}).get('resource')
                for field_def in resource_def['schema'].values()
                if 'data_relation' in field_def)

        # Try yielding until all resources have been yielded.
        while deps:
            # Search for resource without dependencies
            no_deps = [res for res in deps if not deps[res]]
            for resource in no_deps:
                # Yield all elements of that resource
                for item in fixture.get(resource, []):
                    yield (resource, item)
                # Remove it from the list of resources left
                deps.pop(resource)
                # Remove it from dependencies of other resources
                for dep in deps.values():
                    dep.discard(resource)
