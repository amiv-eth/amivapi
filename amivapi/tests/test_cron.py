#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

""" Test scheduler """

from datetime import datetime, timedelta
from freezegun import freeze_time

from amivapi import cron
from amivapi.cron import (
    NotSchedulable,
    periodic,
    run_scheduled_tasks,
    schedulable,
    schedule_once_soon,
    schedule_task,
    update_scheduled_task
)
from amivapi.tests.utils import WebTestNoAuth


class CronTest(WebTestNoAuth):

    has_run = False
    received_arg = None
    run_count = 0

    def setUp(self):
        CronTest.has_run = False
        CronTest.received_arg = None
        CronTest.run_count = 0

        super(CronTest, self).setUp()

    def test_scheduled_function_gets_called(self):
        with self.app.app_context(), freeze_time(
                "2016-01-01 00:00:00") as frozen_time:
            @schedulable
            def scheduled_function(arg):
                CronTest.has_run = True
                CronTest.received_arg = arg

            schedule_task(datetime(2016, 1, 1, 1, 0, 0),
                          scheduled_function,
                          "arg")

            run_scheduled_tasks()

            self.assertFalse(CronTest.has_run)

            frozen_time.tick(delta=timedelta(hours=1))
            run_scheduled_tasks()

            self.assertTrue(CronTest.has_run)
            self.assertEqual(CronTest.received_arg, "arg")

    def test_periodic_func(self):
        with self.app.app_context(), freeze_time(
                "2016-01-01 00:00:00") as frozen_time:
            # We need to define the function in here to make sure the first
            # call is scheduled to the frozen time
            @periodic(timedelta(minutes=5), "arg")
            def periodic_function(arg):
                CronTest.run_count += 1
                CronTest.received_arg = arg

            self.assertEqual(CronTest.run_count, 0)
            run_scheduled_tasks()

            # Check the function has run and got the correct argument
            self.assertEqual(CronTest.run_count, 1)
            self.assertEqual(CronTest.received_arg, "arg")

            # Now check that it is called at correct intervals
            for _ in range(0, 32):
                frozen_time.tick(delta=timedelta(minutes=1))
                run_scheduled_tasks()

            self.assertEqual(CronTest.run_count, 7)

            # Do some cleanup! Else this will get called in other tests..
            cron.periodic_functions.remove(periodic_function)

    def test_scheduling_unknown_function_fails(self):
        with self.app.app_context():
            def test_func():
                pass

            with self.assertRaises(NotSchedulable):
                schedule_task(datetime.utcnow(), test_func)

    def test_schedule_once_soon_works(self):
        with self.app.app_context():
            CronTest.run_count = 0

            @schedulable
            def inc():
                CronTest.run_count += 1

            schedule_once_soon(inc)
            print("nmow")
            schedule_once_soon(inc)

            run_scheduled_tasks()

            self.assertEqual(CronTest.run_count, 1)

    def test_update_scheduled_task(self):
        with self.app.app_context(), freeze_time(
                datetime(2016, 1, 1, 0, 1, 0)) as frozen_time:

            @schedulable
            def tester(arg):
                CronTest.has_run = True
                CronTest.received_arg = arg

            schedule_task(datetime(2016, 1, 2, 4, 20, 0),
                          tester,
                          "arg")

            run_scheduled_tasks()

            self.assertFalse(CronTest.has_run)

            update_scheduled_task(datetime(2017, 1, 2, 4, 20, 0),
                                  tester,
                                  "new-arg")

            frozen_time.tick(delta=timedelta(years=1))
            run_scheduled_tasks()

            self.assertFalse(CronTest.has_run)

            freeze_time.tick(delta=timedelta(months=5))
            run_scheduled_tasks()

            self.assertTrue(CronTest.has_run)
            self.assertEqual(CronTest.received_arg, "new-arg")
