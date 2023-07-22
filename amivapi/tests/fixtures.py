
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

from datetime import date, datetime, timedelta
from os.path import dirname, join
import random
import string
from contextlib import contextmanager

from bson import ObjectId
from eve.methods.post import post_internal
from werkzeug.datastructures import FileStorage

from amivapi.settings import EMAIL_REGEX, REDIRECT_URI_REGEX
from amivapi.utils import admin_permissions


pngpath = join(dirname(__file__), "fixtures", 'lena.png')
jpgpath = join(dirname(__file__), "fixtures", 'lena.jpg')
pdfpath = join(dirname(__file__), "fixtures", 'test.pdf')


class BadFixtureException(Exception):
    """Exception that can be raised for bad tests."""
    pass


class FixtureMixin(object):
    """class to be inherited from to allow fixture loading"""
    @contextmanager
    def writeable_id(self, schema):
        """Make the _id field writeable.

        We often need to manually provide an _id in a fixture, which is
        otherwise blocked by the readonly property.
        """
        _id = self.app.config['ID_FIELD']
        schema[_id]['readonly'] = False
        yield
        schema[_id]['readonly'] = True

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

        # Check that all resources are valid
        fixture_resources = set(fixture.keys())
        all_resources = set(self.app.config['DOMAIN'].keys())
        if not set(fixture_resources).issubset(all_resources):
            raise BadFixtureException("Unknown resources: %s"
                                      % (fixture_resources - all_resources))

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
                with admin_permissions(), self.writeable_id(schema):
                    response, _, _, return_code, _ = post_internal(resource,
                                                                   obj)
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
            if (field not in obj and
                    field_def.get('required', False) and
                    not field_def.get('readonly', False)):
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

    def preprocess_apikeys(self, schema, obj, fixture):
        if 'permissions' not in obj:
            # Create some random permission
            resource = random.choice(list(self.app.config['DOMAIN'].keys()))
            permission = (
                random.choice(schema['permissions']['valuesrules']['allowed']))

            obj['permissions'] = {resource: permission}

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

        # fullfill earlier_than and later_than validators
        obj['time_advertising_start'] = (
            datetime.utcnow() - timedelta(
                seconds=random.randint(0, 1000000)))
        obj['time_advertising_end'] = (
            datetime.utcnow() + timedelta(
                seconds=random.randint(0, 1000000)))

        # add some number of spots. If not specified different, we default
        # to have a signup, so possibly created signups will have something
        # to have relations to
        obj.setdefault('spots', random.randint(50, 500))
        if obj['spots'] is not None:
            if ('time_register_start' not in obj and
                    'time_register_end' not in obj):
                obj['time_register_start'] = (
                    datetime.utcnow() - timedelta(
                        seconds=random.randint(0, 1000000)))
                obj['time_register_end'] = (
                    datetime.utcnow() + timedelta(
                        seconds=random.randint(0, 1000000)))
                obj['time_deregister_end'] = (
                    datetime.utcnow() + timedelta(
                        seconds=random.randint(0, 1000000)))
            else:
                if ('time_register_start' not in obj or
                        'time_register_end' not in obj or
                        'time_deregister_end' not in obj):
                    raise BadFixtureException(
                        "Bad fixture: please specify either all of "
                        "time_register_start, time_register_end "
                        "and time_deregister_end or none")

            obj.setdefault('allow_email_signup',
                           random.choice([True, False]))

            obj.setdefault('selection_strategy',
                           random.choice(['fcfs', 'manual']))

    def preprocess_eventsignups(self, schema, obj, fixture):
        """Find random unique combination of user/event"""
        if 'email' not in obj:
            users = list(obj['user'] if 'user' in obj
                         else u['_id'] for u in self.db['users'].find())
            email = None
        else:
            users = [None]
            email = self.create_random_value(schema['email'])

        events = list(obj['event'] if 'event' in obj
                      else e['_id'] for e in
                      self.db['events'].find({'spots': {'$ne': None}}))

        random.shuffle(events)
        random.shuffle(users)

        for ev in events:
            for u in users:
                if self.db['eventsignups'].count_documents(
                        {'event': ev, 'user': u}) == 0:
                    obj['event'] = ev
                    obj['user'] = u
                    obj['email'] = email
                    return

        raise BadFixtureException("Requested eventsignup creation, but no "
                                  "unique user/event combination is "
                                  "available anymore. Parsed object: %s"
                                  % obj)

    def preprocess_joboffers(self, schema, obj, fixture):
        """Add title to JobOffers to make them valid. """
        obj.setdefault(
            'title_de',
            self.create_random_value(schema['title_de']))
        obj.setdefault(
            'description_de',
            self.create_random_value(schema['description_de']))

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
                letters_and_digits = string.ascii_letters + string.digits
                if definition['regex'] == EMAIL_REGEX:
                    return "%s@%s.%s" % (
                        ''.join(random.choice(letters_and_digits)
                                for _ in range(max(1, length - 27))),
                        ''.join(random.choice(letters_and_digits)
                                for _ in range(20)),
                        ''.join(random.choice(letters_and_digits)
                                for _ in range(5)))
                elif definition['regex'] == REDIRECT_URI_REGEX:
                    return "https://%s" % ''.join(
                        random.choice(letters_and_digits) for _ in range(20))
                raise NotImplementedError

            return ''.join(random.choice(string.ascii_letters + string.digits)
                           for _ in range(length))

        elif t == 'boolean':
            return random.choice([True, False])

        elif t == 'date':
            return datetime.date.fromordinal(
                random.randint(0, date.max.toordinal()))

        elif t == 'datetime':
            return datetime.utcfromtimestamp(
                random.randint(0, 2**32))

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

        elif t == 'media':
            ftype = random.choice(definition.get('filetype', ['zip']))
            if ftype == 'jpg' or ftype == 'jpeg':
                return FileStorage(open(jpgpath, 'rb'), 'test.jpg')
            if ftype == 'png':
                return FileStorage(open(pngpath, 'rb'), 'test.png')
            return FileStorage(open(pdfpath, 'rb'), 'test.pdf')

        elif t == 'list':
            v = []
            for _ in range(0, random.randint(0, 20)):
                default_type = random.choice(['string', 'integer', 'float',
                                              'datetime', 'boolean', 'date',
                                              'media'])
                subschema = definition.get('schema', {'type': default_type})
                v.append(self.create_random_value(subschema))
            return v

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
