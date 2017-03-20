#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""Module to schedule one time tasks or periodic tasks.

1. One time tasks:

You need to register the function to be scheduled with the @schedulable
decorator like this:

@schedulable
def end_of_world(reason):
    print("Terminating world: " + reason)


Now you can schedule the task to be executed at a specific time:

schedule_task(datetime(2012, 12, 21, 12, 0, 0), end_of_world,
              "Maya's calendar ran out of paper or something")

This is of course possible multiple times.


2. Periodic tasks

To schedule a task periodically, use the decorator @periodic like this:

@periodic(timedelta(days=7), "pablo")
def weekly_hello(name):
    print("Hello, %s, another week has passed." % name)

The first execution will happen the first time the scheduler is run.


Notes:
For all kind of scheduled tasks an app context is available, but no request
context. If you need a request context, you can use the flask test client.

The time intervals at which periodic functions are called are subject to
variations depending on when the scheduler is running. This might lead to
drifting of the exact point in time, when a function is called.
For example a function being called at a 24 hour period, is not guaranteed to be
run every day at the same time, but will drift into the future slowly. This
might sum up to a missing period, so after a year the function might have been
called only 364 times.
"""
from datetime import datetime
from functools import wraps
import pickle

from flask import current_app


#
# Public interface
#


class NotSchedulable(Exception):
    pass


def schedulable(func):
    """ Registers a function to be in the table of schedulable functions.
    This is necessary, as we can not save references to python functions in the
    database.
    """
    schedulable_functions[func_str(func)] = func
    return func


def periodic(period, *args):
    """ Decorator to mark a function to be executed periodically.
    Args:
        period: timedelta object describing the time between two calls
        args: arguments to be passed every time
    """
    def wrap(func):
        @wraps(func)
        def wrapped():
            schedule_task(datetime.utcnow() + period, wrapped)
            func(*args)

        schedulable(wrapped)

        # if init_app has already run, schedule the first execution
        if current_app:
            schedule_once_soon(wrapped)
        # As this decorator is run very early, there might not be an app yet.
        # Therefore we save the functions to a list to be scheduled on app init.
        periodic_functions.append(wrapped)

        return wrapped
    return wrap


def schedule_task(time, func, *args):
    """ Schedule a task at some point in the future. """
    func_s = func_str(func)

    if func_s not in schedulable_functions:
        raise NotSchedulable("%s is not schedulable. Did you forget the "
                             "@schedulable decorator?" % func.__name__)

    current_app.data.driver.db['scheduled_tasks'].insert_one({
        'time': time,
        'function': func_s,
        'args': pickle.dumps(args)
    })


def schedule_once_soon(func, *args):
    """ Schedules a function to be run as soon as the scheduler is run the next
    time. Also check, that it is not already scheduled to be run first.
    """
    if current_app.data.driver.db['scheduled_tasks'].find(
            {'function': func_str(func)}).count() != 0:
        return
    schedule_task(datetime.utcnow(), func, *args)


#
# Internal functions
#

schedulable_functions = {}
periodic_functions = []


def func_str(func):
    """ Return a string describing the function """
    return "%s.%s" % (func.__module__, func.__name__)


def run_scheduled_tasks():
    """ Check for scheduled task, which have passed the deadline and run them.
    This needs an app context.
    """
    while True:
        task = (current_app.data.driver.db['scheduled_tasks']
                .find_one_and_delete(
                    {'time': {'$lte': datetime.utcnow()}}))

        if task is None:
            return

        args = pickle.loads(task['args'])
        func = schedulable_functions[task['function']]
        func(*args)


def init_app(app):
    # Periodic functions: If no execution is scheduled so far, schedule one
    with app.app_context():  # this is needed to run db queries
        for func in periodic_functions:
            schedule_once_soon(func)
