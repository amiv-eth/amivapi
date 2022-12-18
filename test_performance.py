#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Run a lot of queries against the API to test response times"""

from amivapi.settings import DATE_FORMAT
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO
from itertools import count
import random
import requests
import statistics
from time import sleep, time
import traceback
from sys import argv, stdout

# Use to generate names. We start at a random number, to make collisions less
# likely, when running this script multiple times.
counter = count(random.randint(0, 0x7fffffff))

# Can be overwriten by command line argument
DEBUG = False

req_session = requests.Session()
req_session.verify = False

#
# Utils
#


class RequestError(Exception):
    pass


def get(url, **kwargs):
    if DEBUG:
        print("GET " + url)
    resp = req_session.get(url, **kwargs)
    if DEBUG:
        print(resp.status_code)
        if resp.status_code != 200:
            print("Request failed:\nURL: %s\nResponse: %s" % (url, resp.json()))
            traceback.print_stack()

    return resp


def post(url, **kwargs):
    if DEBUG:
        print("POST %s, data=%s" % (url, kwargs.get('data')))
    resp = req_session.post(url, **kwargs)
    if DEBUG:
        print(resp.status_code)
        if resp.status_code != 201:
            print("Request failed:\nURL: %s\nResponse: %s" % (url, resp.json()))
            traceback.print_stack()

    return resp


#
# Functions for preparation
#

def create_user():
    data = {
        'nethz': 'user%i' % next(counter),
        'password': 'pass',
        'gender': random.choice(['male', 'female']),
        'firstname': 'Pablo%i' % next(counter),
        'lastname': 'AMIV%i' % next(counter),
        'membership': random.choice(['none', 'regular',
                                     'extraordinary', 'honorary']),
        'email': 'pablo%i@example.com' % next(counter)
    }
    return post(BASE_URL + '/users', data=data,
                auth=(ROOT_PW, '')).json()['_id']


def get_token(username, password):
    data = {
        'username': username,
        'password': password
    }
    return post(BASE_URL + '/sessions', data=data).json()['token']


def create_event():
    data = {
        'title_en': 'event%i' % next(counter),
        'description_en': 'party%i' % next(counter),
        'catchphrase_en': 'dance%i' % next(counter),
        'show_announce': random.choice([True, False]),
        'show_infoscreen': random.choice([True, False]),
        'show_website': random.choice([True, False]),
        'spots': 0,
        'time_register_start': datetime(1970, 1, 1).strftime(DATE_FORMAT),
        'time_register_end': (datetime.utcnow() +
                              timedelta(days=100)).strftime(DATE_FORMAT),
        'time_deregister_end': (datetime.utcnow() +
                              timedelta(days=100)).strftime(DATE_FORMAT),
        'allow_email_signup': True
    }
    return post(BASE_URL + '/events', json=data, auth=(ROOT_PW, '')).json()


def create_studydoc():
    data = {
        'author': 'einstein',
        'name': 'doc%i' % next(counter)
    }
    files = {'files': ('test.txt', BytesIO(b'A' * 10000))}
    return post(BASE_URL + '/studydocuments', data=data,
                files=files, auth=(ROOT_PW, '')).json()


#
# Requests for tests
#


def get_events():
    get(BASE_URL + '/events')


def get_studydocs():
    get(BASE_URL + '/studydocuments', auth=(SESSIONS[0]['token'], ''))


def download_random_studydoc():
    studydocs = get(BASE_URL + '/studydocuments',
                    auth=(SESSIONS[0]['token'], '')).json()['_items']

    # Pick a random doc to download
    doc = random.choice(studydocs)

    # Download the first file of that studydoc
    get(BASE_URL + doc['files'][0]['file'], auth=(SESSIONS[0]['token'], ''))


def random_eventsignup():
    """ Simulate one user signing up for an event """
    user = random.choice(SESSIONS)

    events = get(BASE_URL + '/events').json()['_items']

    event = random.choice(events)

    data = {
        'user': user['id'],
        'event': event['_id']
    }
    post(BASE_URL + '/eventsignups', data=data,
         auth=(user['token'], ''))


#
# Test functions
#

def do_random_get():
    """ Do a random request, however only do GET requests.
    (those might use caching)"""
    try:
        random.choice([get_events,
                       get_studydocs,
                       download_random_studydoc])()
    except Exception as e:
        traceback.print_exc()


def do_random_all():
    """ Do any random request. """
    try:
        random.choice([get_events,
                       get_studydocs,
                       download_random_studydoc,
                       random_eventsignup])()
    except Exception as e:
        traceback.print_exc()


def time_func(func):
    """ Run the supplied function and return the time taken in seconds """
    start = time()
    func()
    elapsed = time() - start
    stdout.write('.')
    stdout.flush()
    return elapsed


def batch_requests(batch_size, batch_time, batch_count,
                   request_func=do_random_all):
    """ Run a performance test, sending batch_size requests every batch_time
    seconds. Do this a total of batch_count times.

    Returns:
         An array of all the request times.
    """
    futures = [None] * (batch_size * batch_count)

    with ThreadPoolExecutor(max_workers=batch_size*batch_count) as executor:
        for i in range(0, batch_count):
            for j in range(0, batch_size):
                futures[i * batch_size + j] = executor.submit(time_func,
                                                              request_func)
            sleep(batch_time)

        return [future.result() for future in futures]


if len(argv) < 3:
    print("Usage: %s <API URL> <root password> [test type] [debug]" % argv[0])
    print("")
    print("Arguments:")
    print("test type: GET or ALL")
    print("debug: True or False")
    exit(1)

BASE_URL = argv[1]
ROOT_PW = argv[2]

TEST_FUNC = do_random_all
if len(argv) > 3:
    if argv[3] == 'GET':
        TEST_FUNC = do_random_get
    elif argv[3] == 'ALL':
        TEST_FUNC = do_random_all
    else:
        print("Error: Invalid test type %s" % argv[3])
        exit(1)

if len(argv) > 4:
    DEBUG = bool(argv[4])


print("Preparation...")
print("Creating some users and sessions...")
with ThreadPoolExecutor(max_workers=100) as executor:
    u_futures = [executor.submit(create_user) for _ in range(100)]
    USERS = [future.result() for future in u_futures]

    s_futures = [(user_id, executor.submit(get_token, user_id, 'pass'))
                 for user_id in USERS]
    SESSIONS = [{'id': user_id, 'token': future.result()}
                for user_id, future in s_futures]

print("Creating some events...")
EVENTS = [create_event() for _ in range(100)]

print("Creating some studydocs...")
STUDYDOCS = [create_studydoc() for _ in range(100)]

times_desc = []
times_mean = []
times_stdev = []

for n_requests in [5000, 5000, 10000, 30000]:
    print("Doing test with %i requests in 30 seconds..." % n_requests)
    time_between_batches = 30. / (n_requests / 10)
    times = batch_requests(10, time_between_batches, n_requests // 10,
                           TEST_FUNC)

    mean = statistics.mean(times)
    stdev = statistics.stdev(times)

    times_desc.append("%i requests in 30 seconds" % n_requests)
    times_mean.append(mean)
    times_stdev.append(stdev)

    print("Finished test.")
    print("Average response time: %.3f s" % mean)
    print("Standard deviation: %.3f s" % stdev)
    print("")


print("Summary:")
print("")
print("%30s|%10s|%10s" % ("Description", "Mean time", "Stdev"))
print("-"*52)
for i in range(0, len(times_desc)):
    print("%30s|%7.2f|%7.2f" % (times_desc[i], times_mean[i], times_stdev[i]))
