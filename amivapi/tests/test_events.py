import datetime as dt

from amivapi import models
from amivapi.tests import util

from amivapi.settings import DATE_FORMAT

import json


class EventTest(util.WebTestNoAuth):

    def test_a_schema(self):
        start = dt.datetime.today() + dt.timedelta(days=2)
        self.api.post("/events", data={
            'title': "Awesome Test Event",
            'time_start': start.strftime(DATE_FORMAT),
            'is_public': True,
            'price': '0',
            'spots': 10,
            'time_register_start': dt.datetime.now().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': json.dumps({
                'department': {
                    'type': 'lol',
                }
            })
        }, status_code=422)
        event_count = self.db.query(models.Event).count()
        self.assertEquals(event_count, 0)

        # make new event with schema that is now json
        self.api.post("/events", data={
            'title': "Awesome Test Event",
            'time_start': start.strftime(DATE_FORMAT),
            'is_public': True,
            'price': '0',
            'spots': 10,
            'time_register_start': dt.datetime.now().strftime(DATE_FORMAT),
            'time_register_end': start.strftime(DATE_FORMAT),
            'additional_fields': 'lol ( %s)' % json.dumps({
                'department': {
                    'type': 'lol',
                }
            })
        }, status_code=422)
        event_count = self.db.query(models.Event).count()
        self.assertEquals(event_count, 0)
